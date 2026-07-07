"""Threat Modeling Agent Module.

Performs security scans and STRIDE threat modeling on code changes by
orchestrating the semgrep scanner and the STRIDE category mapper.

Position in the Semora architecture
-------------------------------------
  ADK Graph Orchestrator (pipeline.py)
      └─> threat_node  ─────────────────> audit_security()  ← THIS MODULE
              ├─> _extract_changed_files()   (parse git diff → file list)
              ├─> run_semgrep()              (semgrep_wrapper.py)
              │       ├─> p/python ruleset
              │       └─> semora_custom_rules.yaml
              └─> map_to_stride() + _classify_severity()  (stride_rules.py)
                      └─> writes RunState.threat_findings

Design notes
------------
* Changed file paths are extracted from ``state.diff_text`` using a regex on
  ``+++ b/<path>`` diff headers, then filtered to Python files only.  Scanning
  is limited to changed files — not the entire repository — to keep runtime
  acceptable on large codebases.

* Full file content is read by semgrep itself (not via the MCP server) because
  the threat node runs in-process inside the ADK graph and has direct, safe
  access to the repository path already stored in ``state.repo_root``.  The
  MCP server is the gateway for *external* agents; internal nodes use the path
  directly.  This is why the task prompt specifies "read full file contents,
  not just the diff" — semgrep is given the full file path and reads the
  complete source, so context-dependent rules (like weak token generation)
  fire correctly even when only a neighbouring line changed.

* SemgrepNotFoundError is caught and re-raised as a RuntimeError with a
  clear install instruction so the CI gate fails with an actionable message
  rather than a bare exception.

Severity classification rules (CRITICAL / HIGH / WARNING)
-----------------------------------------------------------
  CRITICAL  Hardcoded secrets, SQL injection, command injection, eval/exec
            with user input — findings that give an attacker immediate access
            to credentials or the ability to manipulate data/code.

  HIGH      Weak/predictable token generation, path traversal, SSRF —
            findings that require additional exploitation steps but still
            represent a direct security control failure.

  WARNING   Everything else: broad except clauses, minor code-quality smells
            with security implications.
"""

import re
from typing import Any, Union

from semora.graph.state import RunState
from semora.security.semgrep_wrapper import SemgrepNotFoundError, run_semgrep
from semora.security.stride_rules import _normalize_rule_id, map_to_stride

# ---------------------------------------------------------------------------
# Severity classification — rule_id substring patterns
# ---------------------------------------------------------------------------
#
# We match against the *lowercased* rule_id.  More-specific patterns are listed
# first within each tier so they are matched before shorter substrings could
# accidentally swallow them.

_CRITICAL_PATTERNS: frozenset[str] = frozenset({
    # Semora custom rules
    "hardcoded-secret",
    "sql-injection",
    # p/python rules (common substrings)
    "formatted-sql-query",
    "tainted-sql",
    "hardcoded-password",
    "hardcoded-token",
    "command-injection",
    "eval-detected",
    "exec-detected",
    "code-injection",
    "yaml.load",
    "pickle",
    "deserialization",
})

_HIGH_PATTERNS: frozenset[str] = frozenset({
    # Semora custom rules
    "weak-token-generation",
    # p/python rules
    "path-traversal",
    "path-injection",
    "ssrf",
    "open-redirect",
    "xxe",
    "weak-random",
    "insecure-random",
    "md5",
    "sha1",
    "weak-hash",
    "no-auth-over-http",
    "subprocess-shell",
})


def _classify_severity(finding: dict[str, Any]) -> str:
    """Classify a STRIDE-enriched finding as CRITICAL, HIGH, or WARNING.

    Checks the finding's ``rule_id`` (lowercased) for known critical and high
    severity substrings.  Unmatched rules default to WARNING.

    Args:
        finding: An enriched finding dict (output of ``map_to_stride``), which
            must contain at least ``rule_id`` and ``category``.

    Returns:
        One of: ``"CRITICAL"``, ``"HIGH"``, ``"WARNING"``.
    """
    rule_lower: str = _normalize_rule_id(finding.get("rule_id", "")).lower()

    if any(pattern in rule_lower for pattern in _CRITICAL_PATTERNS):
        return "CRITICAL"

    if any(pattern in rule_lower for pattern in _HIGH_PATTERNS):
        return "HIGH"

    # Category-based safety net: Tampering and Elevation of Privilege findings
    # that slipped through the pattern lists are promoted to HIGH rather than
    # left at WARNING, because they represent direct attack capabilities.
    category: str = finding.get("category", "")
    if category.startswith("T —") or category.startswith("E —"):
        return "HIGH"

    return "WARNING"


def _extract_changed_files(diff_text: str, repo_root: str) -> list[str]:
    """Parse a git diff and return absolute paths to changed Python files.

    Looks for ``+++ b/<path>`` headers in the diff output and filters to
    files with a ``.py`` extension.  The ``/dev/null`` placeholder used for
    newly created files is excluded automatically by the ``.py`` filter.

    Args:
        diff_text: Raw git diff text (e.g. from ``git diff --staged``).
        repo_root: Absolute path to the repository root.  Prepended to each
            relative path found in the diff to produce absolute paths for
            semgrep.

    Returns:
        A deduplicated list of absolute paths to changed Python files.
    """
    # Match lines like: +++ b/backend/semora/security/semgrep_wrapper.py
    pattern = re.compile(r"^\+\+\+ b/(.+\.py)$", re.MULTILINE)
    seen: set[str] = set()
    paths: list[str] = []

    for match in pattern.finditer(diff_text):
        rel_path: str = match.group(1)
        if rel_path not in seen:
            seen.add(rel_path)
            paths.append(f"{repo_root.rstrip('/')}/{rel_path}")

    return paths


def audit_security(
    state: Union[dict[str, Any], RunState],
) -> Union[dict[str, Any], RunState]:
    """Run STRIDE security auditing on codebase changes.

    Orchestrates the full security pipeline:
    1. Extracts changed Python file paths from ``state.diff_text``.
    2. Invokes ``run_semgrep`` against those files.
    3. Enriches each raw finding with STRIDE category and suggested patch.
    4. Classifies severity as CRITICAL, HIGH, or WARNING.
    5. Writes a list of 6-key ThreatFinding dicts into ``state.threat_findings``.

    Args:
        state: Current pipeline state, either a ``RunState`` Pydantic model or
            a plain dict with the same top-level keys.

    Returns:
        The updated pipeline state with ``threat_findings`` populated.

    Raises:
        RuntimeError: If semgrep is not installed.  The CI gate must fail with
            a clear install instruction rather than a silent empty result.
    """
    # ------------------------------------------------------------------
    # 1. Unpack state (supports both Pydantic RunState and plain dict)
    # ------------------------------------------------------------------
    is_pydantic: bool = not isinstance(state, dict) and hasattr(state, "repo_path")

    if is_pydantic:
        repo_path: str = state.repo_path
        diff_text: str = state.diff_text
    else:
        repo_path = state.get("repo_path", "")
        diff_text = state.get("diff_text", "")

    # ------------------------------------------------------------------
    # 2. Parse changed Python files from the diff
    # ------------------------------------------------------------------
    changed_files: list[str] = _extract_changed_files(diff_text, repo_path)

    if not changed_files:
        # Nothing to scan — leave threat_findings unchanged.
        return state

    # ------------------------------------------------------------------
    # 3. Invoke semgrep
    #    Full file content is read by semgrep itself (not line-by-line from
    #    the diff) because context-dependent rules — e.g. weak token generation
    #    where the variable name is declared several lines above the random call
    #    — are only detectable with the complete file in scope.
    # ------------------------------------------------------------------
    try:
        raw_findings: list[dict[str, Any]] = run_semgrep(changed_files, repo_path)
    except SemgrepNotFoundError as exc:
        raise RuntimeError(
            f"Security scan aborted: {exc}  "
            "Install semgrep (pip install semgrep) before running Semora."
        ) from exc

    # ------------------------------------------------------------------
    # 4. Enrich, classify, and build the ThreatFinding dicts
    # ------------------------------------------------------------------
    threat_findings: list[dict[str, Any]] = []

    for raw in raw_findings:
        enriched: dict[str, Any] = map_to_stride(raw)
        severity: str = _classify_severity(enriched)

        threat_findings.append({
            "category":        enriched["category"],
            "severity":        severity,
            "file":            enriched["file"],
            "line":            enriched["line"],
            "description":     enriched["description"],
            "suggested_patch": enriched["suggested_patch"],
        })

    # ------------------------------------------------------------------
    # 5. Write findings back into state
    # ------------------------------------------------------------------
    if is_pydantic:
        state.threat_findings = threat_findings
    else:
        state["threat_findings"] = threat_findings

    return state
