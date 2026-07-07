"""Semgrep Scanner Wrapper Module.

Wraps execution of local Semgrep scans against a list of changed file paths,
using Semgrep's default Python-focused ruleset (p/python) plus the project's
own custom rule pack (semora_custom_rules.yaml).

Position in the Semora architecture
-------------------------------------
  threat_node (graph/threat_agent.py)
      └─> run_semgrep()
              ├─> semgrep CLI  ──> p/python       (default Python ruleset)
              └─> semgrep CLI  ──> semora_custom_rules.yaml (hardcoded secrets,
                                                             weak token gen,
                                                             SQL injection)

Design notes
------------
* Semgrep is invoked via ``subprocess.run``; no shell=True is used so there
  is no shell-injection risk from attacker-controlled file paths (each path
  is passed as a separate argv token).
* Semgrep exits with code 1 when it *finds* issues — that is not an error.
  Codes ≥ 2 indicate configuration or runtime failures and are re-raised.
* Binary / non-Python files in ``file_paths`` are silently skipped by
  semgrep itself; we do not pre-filter them here.
* The caller is responsible for ensuring ``file_paths`` contains only files
  that should be scanned (i.e. those extracted from the current git diff).
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, List

# Absolute path to the custom rules YAML, co-located with this module so it
# travels with the package and needs no external configuration.
_CUSTOM_RULES_PATH: Path = Path(__file__).parent / "semora_custom_rules.yaml"


class SemgrepNotFoundError(RuntimeError):
    """Raised when the semgrep CLI binary is not available on PATH.

    Install semgrep with:
        pip install semgrep
    or via the OS package manager.
    """


def run_semgrep(file_paths: List[str], repo_root: str) -> List[dict[str, Any]]:
    """Run semgrep against the given file paths and return normalised findings.

    Invokes semgrep with:
    * ``--config p/python``               — default Python-focused ruleset
    * ``--config <custom_rules>.yaml``    — Semora's hardcoded-secret,
                                            weak-token, and sql-injection rules
    * ``--json``                          — structured output for parsing
    * ``--no-git-ignore``                 — scan exactly the supplied paths,
                                            even if they are gitignored
    * ``--quiet``                         — suppress progress output to stderr

    Args:
        file_paths: Paths to the files to scan.  May be absolute or relative
            to ``repo_root``; semgrep resolves them relative to its CWD which
            is set to ``repo_root``.  An empty list returns immediately with
            no subprocess invocation.
        repo_root: Absolute path to the repository root.  Used as the working
            directory for the semgrep subprocess so relative paths in findings
            are expressed relative to the repo, not the caller's CWD.

    Returns:
        A list of normalised finding dicts.  Each dict contains:

        .. code-block:: python

            {
                "rule_id":  str,  # e.g. "semora.python.hardcoded-secret"
                "file":     str,  # path relative to repo_root
                "line":     int,  # 1-indexed line number of the finding
                "message":  str,  # human-readable description from the rule
                "severity": str,  # raw semgrep severity: ERROR/WARNING/INFO
            }

    Raises:
        SemgrepNotFoundError: If ``semgrep`` is not installed or not on PATH.
        ValueError: If semgrep exits with a code ≥ 2 (configuration / runtime
            failure) or produces non-JSON stdout.
    """
    if shutil.which("semgrep") is None:
        raise SemgrepNotFoundError(
            "semgrep is not installed or not on PATH. "
            "Install it with: pip install semgrep"
        )

    if not file_paths:
        return []

    cmd: List[str] = [
        "semgrep",
        "--config", "p/python",
        "--config", str(_CUSTOM_RULES_PATH),
        "--json",
        "--no-git-ignore",
        "--quiet",
        *file_paths,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=repo_root,
    )

    # semgrep exit codes:
    #   0  — no findings
    #   1  — findings present (normal scan result — NOT an error)
    #   2  — fatal error (bad config, missing file, etc.)
    #   3+ — internal semgrep error
    if result.returncode > 1:
        raise ValueError(
            f"semgrep exited with code {result.returncode}.\n"
            f"stderr: {result.stderr.strip()}"
        )

    try:
        data: dict[str, Any] = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"semgrep produced non-JSON output: {result.stdout[:500]!r}"
        ) from exc

    findings: List[dict[str, Any]] = []
    for raw in data.get("results", []):
        findings.append({
            "rule_id":  raw.get("check_id", "unknown"),
            "file":     raw.get("path", ""),
            "line":     raw.get("start", {}).get("line", 0),
            "message":  raw.get("extra", {}).get("message", ""),
            # Semgrep returns "ERROR" / "WARNING" / "INFO" at the rule level.
            "severity": raw.get("extra", {}).get("severity", "WARNING"),
        })

    return findings
