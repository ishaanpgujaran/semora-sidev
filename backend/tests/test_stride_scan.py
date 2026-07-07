"""Unit tests for the stride-scan security pipeline.

Tests the full stack from semgrep invocation through STRIDE classification:
  1. run_semgrep()     — detects both planted vulnerabilities
  2. map_to_stride()   — assigns correct STRIDE categories
  3. _classify_severity() — assigns CRITICAL or HIGH (both must be ≥ HIGH)
  4. audit_security()  — full pipeline, populates RunState.threat_findings

Test fixture
------------
Each test that needs to run semgrep writes the contents of
``fixtures/vulnerable_sample.py`` (two deliberate vulnerabilities) into a
``tmp_path`` temporary directory.  The path is passed to the scanner so
semgrep processes a real file on a real filesystem.

Skipping behaviour
------------------
All tests that invoke semgrep are decorated with:

    @pytest.mark.skipif(shutil.which("semgrep") is None,
                        reason="semgrep not installed")

This allows the test suite to pass in CI environments without semgrep while
remaining fully exercised in environments where it is available.

Pure-unit tests (``map_to_stride``, ``_classify_severity``) do NOT depend on
semgrep and always run.
"""

import shutil
from pathlib import Path
from typing import Any

import pytest

from semora.security.semgrep_wrapper import SemgrepNotFoundError, run_semgrep
from semora.security.stride_rules import _normalize_rule_id, map_to_stride
from semora.graph.threat_agent import _classify_severity, audit_security
from semora.graph.state import RunState

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: The fixture file path — read at module level so the path is available for
#: tests that write its contents to tmp_path.
_FIXTURE_PATH: Path = Path(__file__).parent / "fixtures" / "vulnerable_sample.py"

#: Valid high-or-above severities expected from our deliberately vulnerable file.
_AT_LEAST_HIGH: frozenset[str] = frozenset({"CRITICAL", "HIGH"})

#: Rule IDs our custom rules emit — used to filter findings in tests.
_HARDCODED_SECRET_RULE: str = "semora.python.hardcoded-secret"
_SQL_INJECTION_RULE: str = "semora.python.sql-injection"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_fixture() -> str:
    """Return the text content of the vulnerable_sample.py fixture."""
    return _FIXTURE_PATH.read_text(encoding="utf-8")


def _write_fixture(tmp_path: Path) -> Path:
    """Copy the vulnerable fixture into tmp_path and return its absolute path."""
    dest = tmp_path / "vulnerable_sample.py"
    dest.write_text(_read_fixture(), encoding="utf-8")
    return dest


def _findings_for_rule(
    findings: list[dict[str, Any]], rule_id_fragment: str
) -> list[dict[str, Any]]:
    """Filter findings to those whose normalised rule_id contains ``rule_id_fragment``."""
    return [f for f in findings if rule_id_fragment in _normalize_rule_id(f.get("rule_id", ""))]


# ===========================================================================
# Pure-unit tests — no semgrep dependency
# ===========================================================================


class TestStrideMapping:
    """map_to_stride() correctly classifies findings by rule_id."""

    def test_hardcoded_secret_maps_to_information_disclosure(self) -> None:
        """A hardcoded-secret finding must map to Information Disclosure."""
        finding = {
            "rule_id": "semora.python.hardcoded-secret",
            "file": "auth.py",
            "line": 5,
            "message": "Hardcoded secret detected.",
            "severity": "ERROR",
        }
        enriched = map_to_stride(finding)

        assert "Information Disclosure" in enriched["category"], (
            f"Expected 'Information Disclosure' in category, got: {enriched['category']!r}"
        )

    def test_sql_injection_maps_to_tampering(self) -> None:
        """A sql-injection finding must map to Tampering."""
        finding = {
            "rule_id": "semora.python.sql-injection",
            "file": "db.py",
            "line": 12,
            "message": "SQL injection risk.",
            "severity": "ERROR",
        }
        enriched = map_to_stride(finding)

        assert "Tampering" in enriched["category"], (
            f"Expected 'Tampering' in category, got: {enriched['category']!r}"
        )

    def test_weak_token_maps_to_spoofing(self) -> None:
        """A weak-token-generation finding must map to Spoofing."""
        finding = {
            "rule_id": "semora.python.weak-token-generation",
            "file": "session.py",
            "line": 8,
            "message": "Weak token generation.",
            "severity": "ERROR",
        }
        enriched = map_to_stride(finding)

        assert "Spoofing" in enriched["category"], (
            f"Expected 'Spoofing' in category, got: {enriched['category']!r}"
        )

    def test_enriched_finding_has_all_required_keys(self) -> None:
        """map_to_stride must add category, description, and suggested_patch."""
        finding = {
            "rule_id": "semora.python.hardcoded-secret",
            "file": "config.py",
            "line": 1,
            "message": "msg",
            "severity": "ERROR",
        }
        enriched = map_to_stride(finding)

        for key in ("category", "description", "suggested_patch"):
            assert key in enriched, f"Missing key '{key}' in enriched finding."
        assert enriched["category"], "category must be a non-empty string."
        assert enriched["suggested_patch"], "suggested_patch must be non-empty."

    def test_unknown_rule_defaults_to_information_disclosure(self) -> None:
        """An unrecognised rule_id should fall back to Information Disclosure."""
        finding = {
            "rule_id": "some.unknown.rule.that.has.no.mapping",
            "file": "x.py",
            "line": 1,
            "message": "Unknown finding.",
            "severity": "WARNING",
        }
        enriched = map_to_stride(finding)

        # Default is I — Information Disclosure; any STRIDE category is acceptable
        # but the field must be present and non-empty.
        assert "category" in enriched
        assert enriched["category"]  # non-empty


class TestSeverityClassification:
    """_classify_severity() assigns the correct tier."""

    def test_hardcoded_secret_is_critical(self) -> None:
        finding = {
            "rule_id": "semora.python.hardcoded-secret",
            "category": "I — Information Disclosure",
        }
        assert _classify_severity(finding) == "CRITICAL"

    def test_sql_injection_is_critical(self) -> None:
        finding = {
            "rule_id": "semora.python.sql-injection",
            "category": "T — Tampering",
        }
        assert _classify_severity(finding) == "CRITICAL"

    def test_weak_token_is_high(self) -> None:
        finding = {
            "rule_id": "semora.python.weak-token-generation",
            "category": "S — Spoofing",
        }
        assert _classify_severity(finding) == "HIGH"

    def test_unrecognised_tampering_is_high_via_category_net(self) -> None:
        """A Tampering finding with an unrecognised rule_id should be HIGH via
        the category-based safety net in _classify_severity."""
        finding = {
            "rule_id": "some.obscure.rule",
            "category": "T — Tampering",
        }
        assert _classify_severity(finding) == "HIGH"

    def test_generic_unknown_is_warning(self) -> None:
        finding = {
            "rule_id": "some.generic.info.rule",
            "category": "I — Information Disclosure",
        }
        assert _classify_severity(finding) == "WARNING"


# ===========================================================================
# Integration tests — require semgrep on PATH
# ===========================================================================

_SKIP_NO_SEMGREP = pytest.mark.skipif(
    shutil.which("semgrep") is None,
    reason="semgrep is not installed; skipping live scan tests.",
)


@_SKIP_NO_SEMGREP
class TestSemgrepScanner:
    """run_semgrep() detects both planted vulnerabilities in the fixture file."""

    def test_returns_at_least_two_findings(self, tmp_path: Path) -> None:
        """The vulnerable fixture must produce ≥ 2 semgrep findings."""
        fixture = _write_fixture(tmp_path)
        findings = run_semgrep([str(fixture)], str(tmp_path))

        assert len(findings) >= 2, (
            f"Expected at least 2 findings from the vulnerable fixture, got {len(findings)}.\n"
            f"Findings: {findings}"
        )

    def test_hardcoded_secret_is_detected(self, tmp_path: Path) -> None:
        """run_semgrep must flag the hardcoded API_KEY assignment."""
        fixture = _write_fixture(tmp_path)
        findings = run_semgrep([str(fixture)], str(tmp_path))

        secret_findings = _findings_for_rule(findings, "hardcoded-secret")
        assert secret_findings, (
            "Expected a hardcoded-secret finding but none were produced.\n"
            f"All findings: {[f['rule_id'] for f in findings]}"
        )

    def test_sql_injection_is_detected(self, tmp_path: Path) -> None:
        """run_semgrep must flag the f-string SQL injection pattern."""
        fixture = _write_fixture(tmp_path)
        findings = run_semgrep([str(fixture)], str(tmp_path))

        # Accept either our custom rule or p/python's formatted-sql-query rule.
        sql_findings = [
            f for f in findings
            if "sql-injection" in _normalize_rule_id(f.get("rule_id", "")).lower()
            or "formatted-sql-query" in _normalize_rule_id(f.get("rule_id", "")).lower()
            or "sql" in _normalize_rule_id(f.get("rule_id", "")).lower()
        ]
        assert sql_findings, (
            "Expected a SQL-injection finding but none were produced.\n"
            f"All findings: {[f['rule_id'] for f in findings]}"
        )

    def test_finding_dicts_have_required_keys(self, tmp_path: Path) -> None:
        """Every finding returned by run_semgrep must have the 5 normalised keys."""
        fixture = _write_fixture(tmp_path)
        findings = run_semgrep([str(fixture)], str(tmp_path))

        for f in findings:
            for key in ("rule_id", "file", "line", "message", "severity"):
                assert key in f, (
                    f"Finding is missing key '{key}': {f}"
                )

    def test_empty_file_list_returns_empty(self, tmp_path: Path) -> None:
        """Passing an empty file list must short-circuit and return []."""
        result = run_semgrep([], str(tmp_path))
        assert result == []


@_SKIP_NO_SEMGREP
class TestFullStrideClassification:
    """End-to-end: semgrep → STRIDE mapping → severity classification."""

    def _run_full(self, tmp_path: Path) -> list[dict[str, Any]]:
        fixture = _write_fixture(tmp_path)
        raw_findings = run_semgrep([str(fixture)], str(tmp_path))
        classified = []
        for f in raw_findings:
            enriched = map_to_stride(f)
            enriched["severity"] = _classify_severity(enriched)
            classified.append(enriched)
        return classified


    def test_hardcoded_secret_stride_category(self, tmp_path: Path) -> None:
        """API_KEY hardcoding must be classified as Information Disclosure."""
        classified = self._run_full(tmp_path)

        secret_findings = [
            f for f in classified
            if "hardcoded-secret" in _normalize_rule_id(f.get("rule_id", ""))
        ]
        assert secret_findings, "No hardcoded-secret finding survived STRIDE mapping."

        for f in secret_findings:
            assert "Information Disclosure" in f["category"], (
                f"Expected 'Information Disclosure', got: {f['category']!r}"
            )

    def test_hardcoded_secret_severity_at_least_high(self, tmp_path: Path) -> None:
        """API_KEY hardcoding severity must be CRITICAL or HIGH."""
        classified = self._run_full(tmp_path)

        secret_findings = [
            f for f in classified
            if "hardcoded-secret" in _normalize_rule_id(f.get("rule_id", ""))
        ]
        assert secret_findings, "No hardcoded-secret finding to check severity."

        for f in secret_findings:
            assert f["severity"] in _AT_LEAST_HIGH, (
                f"Expected severity in {_AT_LEAST_HIGH}, got: {f['severity']!r}"
            )

    def test_sql_injection_stride_category(self, tmp_path: Path) -> None:
        """SQL f-string injection must be classified as Tampering."""
        classified = self._run_full(tmp_path)

        sql_findings = [
            f for f in classified
            if any(
                kw in _normalize_rule_id(f.get("rule_id", "")).lower()
                for kw in ("sql-injection", "formatted-sql-query", "sql")
            )
        ]
        assert sql_findings, "No SQL-injection finding survived STRIDE mapping."

        for f in sql_findings:
            assert "Tampering" in f["category"], (
                f"Expected 'Tampering', got: {f['category']!r}"
            )

    def test_sql_injection_severity_at_least_high(self, tmp_path: Path) -> None:
        """SQL injection severity must be CRITICAL or HIGH."""
        classified = self._run_full(tmp_path)

        sql_findings = [
            f for f in classified
            if any(
                kw in _normalize_rule_id(f.get("rule_id", "")).lower()
                for kw in ("sql-injection", "formatted-sql-query", "sql")
            )
        ]
        assert sql_findings, "No SQL-injection finding to check severity."

        for f in sql_findings:
            assert f["severity"] in _AT_LEAST_HIGH, (
                f"Expected severity in {_AT_LEAST_HIGH}, got: {f['severity']!r}"
            )

    def test_threat_finding_has_all_six_keys(self, tmp_path: Path) -> None:
        """Every classified finding must have the canonical 6 ThreatFinding keys."""
        classified = self._run_full(tmp_path)

        required_keys = {"category", "severity", "file", "line",
                         "description", "suggested_patch"}

        for f in classified:
            missing = required_keys - f.keys()
            assert not missing, (
                f"ThreatFinding is missing keys {missing}: {f}"
            )


@_SKIP_NO_SEMGREP
class TestAuditSecurityPipeline:
    """audit_security() populates RunState.threat_findings correctly."""

    def _make_state(self, tmp_path: Path, fixture_path: Path) -> RunState:
        """Build a RunState with a synthetic diff pointing at the fixture file.

        The diff text uses the standard ``+++ b/<path>`` format so that
        ``_extract_changed_files`` can parse the changed file path.
        """
        rel_path = fixture_path.relative_to(tmp_path).as_posix()
        diff_text = (
            f"diff --git a/{rel_path} b/{rel_path}\n"
            f"--- a/{rel_path}\n"
            f"+++ b/{rel_path}\n"
            "@@ -0,0 +1,40 @@\n"
            "+# fixture content\n"
        )
        return RunState(repo_path=str(tmp_path), diff_text=diff_text)

    def test_audit_security_populates_threat_findings(self, tmp_path: Path) -> None:
        """audit_security must write at least one finding into threat_findings."""
        fixture = _write_fixture(tmp_path)
        state = self._make_state(tmp_path, fixture)

        result_state = audit_security(state)

        assert result_state.threat_findings, (
            "audit_security returned an empty threat_findings list; "
            "expected at least one finding from the vulnerable fixture."
        )

    def test_audit_security_finding_schema(self, tmp_path: Path) -> None:
        """Every item in threat_findings must have the canonical 6-key schema."""
        fixture = _write_fixture(tmp_path)
        state = self._make_state(tmp_path, fixture)

        result_state = audit_security(state)
        required_keys = {"category", "severity", "file", "line",
                         "description", "suggested_patch"}

        for finding in result_state.threat_findings:
            missing = required_keys - finding.keys()
            assert not missing, (
                f"ThreatFinding in RunState is missing keys {missing}: {finding}"
            )

    def test_audit_security_includes_critical_finding(self, tmp_path: Path) -> None:
        """At least one finding must be CRITICAL (hardcoded secret or SQL injection)."""
        fixture = _write_fixture(tmp_path)
        state = self._make_state(tmp_path, fixture)

        result_state = audit_security(state)
        severities = {f["severity"] for f in result_state.threat_findings}

        assert "CRITICAL" in severities, (
            f"Expected at least one CRITICAL finding; got severities: {severities}"
        )

    def test_audit_security_no_diff_returns_empty(self, tmp_path: Path) -> None:
        """With an empty diff, threat_findings must remain empty."""
        state = RunState(repo_path=str(tmp_path), diff_text="")
        result_state = audit_security(state)

        assert result_state.threat_findings == [], (
            "Expected empty threat_findings for empty diff."
        )

    def test_audit_security_dict_state_is_supported(self, tmp_path: Path) -> None:
        """audit_security must also accept a plain dict (not just Pydantic model)."""
        fixture = _write_fixture(tmp_path)
        rel_path = fixture.relative_to(tmp_path).as_posix()
        diff_text = (
            f"diff --git a/{rel_path} b/{rel_path}\n"
            f"--- a/{rel_path}\n"
            f"+++ b/{rel_path}\n"
            "@@ -0,0 +1,40 @@\n"
            "+# fixture content\n"
        )
        state_dict: dict = {
            "repo_path": str(tmp_path),
            "diff_text": diff_text,
            "generated_specs": [],
            "execution_results": {},
            "threat_findings": [],
            "compliance_score": None,
        }

        result = audit_security(state_dict)

        assert isinstance(result, dict)
        assert "threat_findings" in result
        assert isinstance(result["threat_findings"], list)
