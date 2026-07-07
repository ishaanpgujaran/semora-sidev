"""Sandbox Runner Module.

Manages execution of BDD tests and scripts inside a persistent, reusable,
isolated sandbox subprocess. Communicates via JSON lines over stdin/stdout,
applying timeout and filesystem isolation policies.
"""

import os
import sys
import json
import time
import shutil
import select
import tempfile
import subprocess
from typing import Dict, Any, Optional

# Singleton runner instance
_runner_instance: Optional["SandboxRunner"] = None


class SandboxRunner:
    """Subprocess manager that maintains a long-lived, reusable sandbox worker.

    Monitors stdout for response or timeout, automatically recreating the worker
    if it crashes, violates safety rules, or hangs.
    """

    def __init__(self, memory_limit_mb: int = 256) -> None:
        self.memory_limit_mb = memory_limit_mb
        self.proc: Optional[subprocess.Popen] = None

    def start_worker(self) -> None:
        """Spawn the persistent background worker process."""
        if self.proc and self.proc.poll() is None:
            return  # Already running

        # Build path to worker.py sibling module
        worker_path = os.path.join(os.path.dirname(__file__), "worker.py")

        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        self.proc = subprocess.Popen(
            [sys.executable, worker_path, str(self.memory_limit_mb)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            env=env
        )

    def kill_worker(self) -> None:
        """Terminate the running worker process and reset references."""
        if self.proc:
            try:
                self.proc.kill()
                self.proc.wait(timeout=1.0)
            except Exception:
                pass
            self.proc = None

    def run(
        self,
        code: Optional[str] = None,
        command: Optional[str] = None,
        temp_dir: Optional[str] = None,
        repo_path: Optional[str] = None,
        timeout_seconds: float = 5.0
    ) -> Dict[str, Any]:
        """Send code or command execution payload to the worker and return results.

        Enforces a hard timeout and intercepts sandbox safety violations.
        """
        self.start_worker()
        assert self.proc is not None
        assert self.proc.stdin is not None
        assert self.proc.stdout is not None

        # Build JSON input payload
        payload_dict = {
            "code": code or "",
            "command": command or "",
            "temp_dir": os.path.abspath(temp_dir) if temp_dir else "",
            "repo_path": os.path.abspath(repo_path) if repo_path else ""
        }
        payload = json.dumps(payload_dict) + "\n"

        try:
            self.proc.stdin.write(payload)
            self.proc.stdin.flush()
        except (IOError, ValueError):
            # Worker was dead or closed. Restart and try one more time
            self.kill_worker()
            self.start_worker()
            try:
                assert self.proc is not None
                assert self.proc.stdin is not None
                self.proc.stdin.write(payload)
                self.proc.stdin.flush()
            except Exception as e:
                return {
                    "returncode": -1,
                    "stdout": "",
                    "stderr": f"Failed to communicate with sandbox worker: {e}",
                    "status": "SANDBOX_VIOLATION"
                }

        # Non-blocking wait for stdout pipe with select
        try:
            assert self.proc.stdout is not None
            r, _, _ = select.select([self.proc.stdout], [], [], timeout_seconds)
        except Exception as e:
            self.kill_worker()
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"Select communication error: {e}",
                "status": "SANDBOX_VIOLATION"
            }

        if not r:
            # Execution timed out! Kill worker process and report violation
            self.kill_worker()
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"SANDBOX_VIOLATION: Execution timed out (exceeded {timeout_seconds}s limit)",
                "status": "SANDBOX_VIOLATION"
            }

        # Read JSON response line from worker
        try:
            line = self.proc.stdout.readline()
            if not line:
                # EOF reached. Subprocess died. Check exit code
                exit_code = self.proc.poll()
                worker_stderr = ""
                if self.proc.stderr:
                    try:
                        # Use a non-blocking read or read up to EOF since process has died
                        worker_stderr = self.proc.stderr.read().strip()
                    except Exception:
                        pass
                self.kill_worker()
                if exit_code == 99:
                    return {
                        "returncode": 99,
                        "stdout": "",
                        "stderr": worker_stderr or "SANDBOX_VIOLATION: Code attempted unauthorized file write or process spawn",
                        "status": "SANDBOX_VIOLATION"
                    }
                else:
                    return {
                        "returncode": exit_code if exit_code is not None else -1,
                        "stdout": "",
                        "stderr": worker_stderr or f"Sandbox process exited unexpectedly with code {exit_code}",
                        "status": "SANDBOX_VIOLATION"
                    }

            response = json.loads(line)
            return {
                "returncode": response.get("returncode", 0),
                "stdout": response.get("stdout", ""),
                "stderr": response.get("stderr", ""),
                "status": response.get("status", "SUCCESS")
            }
        except Exception as e:
            self.kill_worker()
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"Failed to parse sandbox response: {e}",
                "status": "SANDBOX_VIOLATION"
            }


def get_runner() -> SandboxRunner:
    """Retrieve or initialize the global SandboxRunner instance."""
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = SandboxRunner()
    return _runner_instance


def run_in_sandbox(command: str, repo_path: Optional[str] = None) -> Dict[str, Any]:
    """Execute a system command in a safe, sandboxed wrapper.

    Generates a localized temp directory for filesystem write policies,
    cleans up upon exit, and returns execution status.

    Args:
        command (str): Command to be executed.
        repo_path (str, optional): Target repository root directory.

    Returns:
        Dict[str, Any]: Result mapping containing returncode, stdout, stderr, and status.
    """
    runner = get_runner()
    # Create local temporary directory for execution
    temp_dir = tempfile.mkdtemp(prefix="semora-sandbox-")
    try:
        result = runner.run(command=command, temp_dir=temp_dir, repo_path=repo_path)
        return result
    finally:
        # Clean up temp directory
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
