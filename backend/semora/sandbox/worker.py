"""Sandbox Subprocess Worker.

This module acts as the isolated execution context for test code. It runs as
a persistent background daemon communicating over stdin/stdout via JSON.
It enforces Unix-level memory limits and PEP 578 audit hooks to restrict
file system writes to an allowed temporary directory and to block sandbox escapes
(such as spawning subprocesses).
"""

import sys
import os
import json
import io
import traceback
from typing import Optional

# Save the original stdout/stderr for communicating with manager
ORIGINAL_STDOUT = sys.stdout
ORIGINAL_STDERR = sys.stderr

# Disable compilation of bytecode files globally in this process
sys.dont_write_bytecode = True

# Memory limit from command-line arguments (default 256MB)
memory_limit_mb = 256
if len(sys.argv) > 1:
    try:
        memory_limit_mb = int(sys.argv[1])
    except ValueError:
        pass

# Enforce memory limits (Unix only)
try:
    import resource
    limit_bytes = memory_limit_mb * 1024 * 1024
    soft_max, hard_max = resource.getrlimit(resource.RLIMIT_AS)
    # Capping soft limit to memory limit, hard limit stays as maximum allowed
    resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, hard_max))
except Exception:
    # Quietly pass on environments where RLIMIT_AS cannot be modified (e.g. macOS)
    pass

# Global variable to track the currently allowed temp directory for file writes
ALLOWED_TEMP_DIR: Optional[str] = None


def audit_hook(event: str, args: tuple) -> None:
    """PEP 578 runtime audit hook to enforce sandbox containment.

    Blocks all subprocess spawning (sandbox escape attempts) and restricts
    filesystem write/modification operations to the ALLOWED_TEMP_DIR when set.
    """
    global ALLOWED_TEMP_DIR

    # Block subprocess and fork operations to prevent sandbox escape
    if event in ("subprocess.Popen", "os.system", "os.exec", "os.fork", "os.posix_spawn", "os.spawn"):
        print(f"SANDBOX_VIOLATION: Spawning subprocesses is blocked: {event}", file=ORIGINAL_STDERR)
        os._exit(99)

    if ALLOWED_TEMP_DIR is not None:
        if event == "open":
            path, mode, flags = args
            # If opening a file for writing, appending, or editing
            if mode and any(char in mode for char in "wax+"):
                abs_path = os.path.abspath(path)
                # Allow writing to system devnull (e.g. for stdout/stderr redirection)
                if abs_path == os.path.abspath(os.devnull) or abs_path == "/dev/null":
                    return
                if not abs_path.startswith(ALLOWED_TEMP_DIR):
                    print(f"SANDBOX_VIOLATION: Write blocked outside temp directory: {abs_path}", file=ORIGINAL_STDERR)
                    os._exit(99)
        elif event in ("os.mkdir", "os.rmdir", "os.remove", "os.unlink", "os.rename", "os.link", "os.symlink"):
            path = args[0]
            abs_path = os.path.abspath(path)
            if not abs_path.startswith(ALLOWED_TEMP_DIR):
                print(f"SANDBOX_VIOLATION: Filesystem modification blocked: {event} on {abs_path}", file=ORIGINAL_STDERR)
                os._exit(99)


# Register the audit hook at worker startup
sys.addaudithook(audit_hook)


def run_command_in_process(command_str: str) -> int:
    """Execute a system command in-process within the worker workspace.

    Handles pytest and python file/code execution programmatically to preserve
    in-process audit hooks.

    Args:
        command_str (str): The command line string to run.

    Returns:
        int: The exit/return code of the execution.
    """
    import shlex
    args = shlex.split(command_str)
    if not args:
        return 0

    # Handle pytest commands: e.g. "pytest tests/features/xxx.feature"
    if args[0] == "pytest" or (len(args) > 2 and args[0] == "python" and args[1] == "-m" and args[2] == "pytest"):
        import pytest
        pytest_args = args[1:] if args[0] == "pytest" else args[3:]
        # Run pytest.main, which returns an ExitCode int
        return int(pytest.main(pytest_args))

    # Handle python commands
    if args[0] == "python":
        if len(args) > 2 and args[1] == "-c":
            globals_dict = {"__builtins__": __builtins__}
            locals_dict = {}
            exec(args[2], globals_dict, locals_dict)
            return 0
        elif len(args) > 1:
            script_path = args[1]
            sys.argv = args[1:]
            with open(script_path, "r", encoding="utf-8") as f:
                globals_dict = {"__builtins__": __builtins__, "__file__": script_path}
                locals_dict = {}
                exec(f.read(), globals_dict, locals_dict)
            return 0

    # Otherwise, reject to maintain the sandbox boundary
    raise RuntimeError(f"Command not supported inside the in-process sandbox: {command_str}")


def main() -> None:
    """Main loop reading from stdin and writing results to stdout."""
    global ALLOWED_TEMP_DIR

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break  # stdin closed, exit worker

            request = json.loads(line)
            code = request.get("code", "")
            command = request.get("command", "")
            temp_dir = request.get("temp_dir", "")
            repo_path = request.get("repo_path", "")

            # Set the allowed directory for this execution
            original_env_temp = {}
            original_tempfile_dir = None
            if temp_dir:
                ALLOWED_TEMP_DIR = os.path.abspath(temp_dir)
                import tempfile
                original_tempfile_dir = tempfile.tempdir
                tempfile.tempdir = ALLOWED_TEMP_DIR

                for var in ("TMPDIR", "TEMP", "TMP"):
                    original_env_temp[var] = os.environ.get(var)
                    os.environ[var] = ALLOWED_TEMP_DIR
            else:
                ALLOWED_TEMP_DIR = None

            # Change to target repository directory if provided
            original_cwd = os.getcwd()
            if repo_path:
                try:
                    os.chdir(repo_path)
                except Exception as e:
                    print(f"Failed to change CWD to {repo_path}: {e}", file=ORIGINAL_STDERR)

            # Capture stdout/stderr streams
            captured_stdout = io.StringIO()
            captured_stderr = io.StringIO()

            sys.stdout = captured_stdout
            sys.stderr = captured_stderr

            returncode = 0
            status = "SUCCESS"

            try:
                if code:
                    globals_dict = {"__builtins__": __builtins__}
                    locals_dict = {}
                    exec(code, globals_dict, locals_dict)
                elif command:
                    returncode = run_command_in_process(command)
                else:
                    raise ValueError("Neither 'code' nor 'command' provided.")
            except SystemExit as se:
                returncode = se.code if isinstance(se.code, int) else 0
            except Exception as e:
                returncode = 1
                status = "ERROR"
                traceback.print_exc(file=captured_stderr)
            finally:
                # Restore original streams, directory, allowed temp dir, tempfile cache, and environment variables
                sys.stdout = ORIGINAL_STDOUT
                sys.stderr = ORIGINAL_STDERR
                ALLOWED_TEMP_DIR = None
                import tempfile
                tempfile.tempdir = original_tempfile_dir
                for var, val in original_env_temp.items():
                    if val is None:
                        os.environ.pop(var, None)
                    else:
                        os.environ[var] = val
                if repo_path:
                    try:
                        os.chdir(original_cwd)
                    except Exception:
                        pass

            # Send execution result back to manager
            response = {
                "status": status,
                "returncode": returncode,
                "stdout": captured_stdout.getvalue(),
                "stderr": captured_stderr.getvalue()
            }
            ORIGINAL_STDOUT.write(json.dumps(response) + "\n")
            ORIGINAL_STDOUT.flush()

        except Exception as e:
            # Fatal parser/JSON crash - print details and hard exit
            try:
                sys.stdout = ORIGINAL_STDOUT
                sys.stderr = ORIGINAL_STDERR
                ORIGINAL_STDERR.write(f"Worker loop crash: {e}\n")
                ORIGINAL_STDERR.flush()
            except Exception:
                pass
            os._exit(1)


if __name__ == "__main__":
    main()
