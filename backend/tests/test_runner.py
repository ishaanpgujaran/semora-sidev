"""Test suite for the Semora Sandbox Runner.

Verifies that the SandboxRunner maintains a persistent worker process, executes
valid Python commands, enforces timeouts, blocks unauthorized filesystem writes,
blocks subprocess spawning, and recovers transparently after process termination.
"""

import os
import tempfile
import pytest
from pathlib import Path

from semora.sandbox.runner import run_in_sandbox, get_runner


def test_valid_command_execution() -> None:
    """Verify that a standard valid command executes successfully."""
    # Run a simple python print command
    result = run_in_sandbox('python -c "print(\'hello from sandbox\')"')
    assert result["status"] == "SUCCESS"
    assert result["returncode"] == 0
    assert "hello from sandbox" in result["stdout"]


def test_sandbox_timeout_enforcement() -> None:
    """Verify that commands exceeding the timeout are killed and flagged as violation."""
    # Sleeping for 10 seconds (exceeds the 5.0 seconds limit)
    result = run_in_sandbox('python -c "import time; time.sleep(10)"')
    assert result["status"] == "SANDBOX_VIOLATION"
    assert "timed out" in result["stderr"]


def test_sandbox_write_isolation() -> None:
    """Verify that file writes outside the temp directory are blocked and trigger violation."""
    runner = get_runner()
    # Create an allowed temp directory
    with tempfile.TemporaryDirectory() as allowed_dir:
        # 1. Attempt writing inside the allowed directory (should succeed)
        allowed_file_path = os.path.join(allowed_dir, "test_write.txt")
        code_allowed = f"with open('{allowed_file_path}', 'w') as f: f.write('allowed')"
        result_allowed = runner.run(code=code_allowed, temp_dir=allowed_dir)
        assert result_allowed["status"] == "SUCCESS"
        assert os.path.exists(allowed_file_path)
        assert Path(allowed_file_path).read_text() == "allowed"

        # 2. Attempt writing outside the allowed directory (should violate sandbox and terminate worker)
        # We try to write to a path outside the temp directory, e.g., a sibling folder or system tmp
        disallowed_file_path = os.path.join(tempfile.gettempdir(), "test_violation.txt")
        # Cleanup in case it existed
        try:
            os.remove(disallowed_file_path)
        except OSError:
            pass

        code_disallowed = f"with open('{disallowed_file_path}', 'w') as f: f.write('disallowed')"
        result_disallowed = runner.run(code=code_disallowed, temp_dir=allowed_dir)

        assert result_disallowed["status"] == "SANDBOX_VIOLATION"
        assert not os.path.exists(disallowed_file_path)


def test_sandbox_process_spawn_blocking() -> None:
    """Verify that any attempt to spawn a subprocess is blocked and terminates the worker."""
    runner = get_runner()
    with tempfile.TemporaryDirectory() as allowed_dir:
        code_spawn = "import subprocess; subprocess.Popen(['ls'])"
        result = runner.run(code=code_spawn, temp_dir=allowed_dir)
        assert result["status"] == "SANDBOX_VIOLATION"
        assert "Spawning subprocesses is blocked" in result["stderr"] or "Code attempted unauthorized" in result["stderr"]


def test_sandbox_resiliency_and_restart() -> None:
    """Verify that the manager transparently recovers and runs subsequent commands after a crash/violation."""
    # 1. Trigger a violation (which kills the current worker)
    result_violation = run_in_sandbox('python -c "import os; os._exit(99)"')
    assert result_violation["status"] == "SANDBOX_VIOLATION"

    # 2. Run a subsequent valid command (which should start a new worker and succeed)
    result_valid = run_in_sandbox('python -c "print(\'resilient worker\')"')
    assert result_valid["status"] == "SUCCESS"
    assert "resilient worker" in result_valid["stdout"]
