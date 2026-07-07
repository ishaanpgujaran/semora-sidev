---
name: stride-scan
description: >
  Use this skill when you need to perform STRIDE threat modeling on changed
  Python files in the Semora pipeline.  Trigger it when a task involves:
  "scan for security vulnerabilities", "run stride analysis", "check for
  hardcoded secrets", "audit this diff for threats", or "populate
  threat_findings in RunState".  Provides the canonical schema for
  ThreatFinding dicts, severity classification rules, STRIDE category
  mapping rationale, and references to the concrete implementation modules.
---

# stride-scan: STRIDE Threat Modeling Skill

This skill encapsulates the Security Agent's capability to scan changed Python
files for security vulnerabilities, map each finding to a STRIDE category, and
populate `RunState.threat_findings` in the Semora ADK Graph Workflow.

---

## 1. Implementation Modules

| Module | Role |
|--------|------|
| [`backend/semora/security/semgrep_wrapper.py`](../../../backend/semora/security/semgrep_wrapper.py) | Invokes the `semgrep` CLI via `subprocess`, returns normalized finding dicts |
| [`backend/semora/security/semora_custom_rules.yaml`](../../../backend/semora/security/semora_custom_rules.yaml) | Three custom Semgrep rules for patterns not well covered by `p/python` defaults |
| [`backend/semora/security/stride_rules.py`](../../../backend/semora/security/stride_rules.py) | Maps each finding to a STRIDE category and generates a `suggested_patch` |
| [`backend/semora/graph/threat_agent.py`](../../../backend/semora/graph/threat_agent.py) | ADK graph node: orchestrates the scan, classifies severity, writes `RunState.threat_findings` |

---

## 2. Canonical ThreatFinding Schema

Every item written to `RunState.threat_findings` **must** contain exactly
these six keys:

```python
{
    "category":        str,   # STRIDE category, e.g. "I — Information Disclosure"
    "severity":        str,   # "CRITICAL" | "HIGH" | "WARNING"
    "file":            str,   # Relative path to the affected file
    "line":            int,   # Line number reported by semgrep
    "description":     str,   # Human-readable explanation of the threat
    "suggested_patch": str,   # Short inline code suggestion (not a full diff)
}
```

---

## 3. Severity Classification Rules

| Severity  | When to apply |
|-----------|---------------|
| `CRITICAL` | Hardcoded secrets/API keys, SQL injection, command injection, `eval`/`exec` with user input |
| `HIGH`     | Weak/predictable token generation (`random.*` for security values), path traversal, SSRF |
| `WARNING`  | Everything else: broad `except:`, insecure deserialisation hints, etc. |

> A `CRITICAL` finding **must** force the Aggregator's compliance gate to fail
> (`compliance_score = 0`).  The Reporting & Sync Agent owns this gate logic.

---

## 4. STRIDE Category Mapping Rationale

The mapping from vulnerability type → STRIDE category is intentionally
**subjective**; the comments in `stride_rules.py` justify each choice.
The table below is the authoritative summary:

| Vulnerability pattern | STRIDE | Rationale |
|-----------------------|--------|-----------|
| Hardcoded secrets / API keys | **I — Information Disclosure** | Credentials baked into source are readable by anyone with repo access, directly disclosing access tokens |
| SQL injection (f-string / concat) | **T — Tampering** | Attacker-controlled input modifies the data the query reads or writes |
| Weak token generation (`random.*`) | **S — Spoofing** | `random` is not cryptographically secure; guessable tokens let an attacker forge a valid session and impersonate a user |
| Bare `except:` / exception swallow | **R — Repudiation** | Silent failure hides attack traces, making malicious actions non-attributable |
| `eval()` / `exec()` with user input | **E — Elevation of Privilege** | Arbitrary code execution grants the attacker the process's full privilege level |
| Path traversal / unbounded reads | **D — Denial of Service** | Reading attacker-controlled paths can exhaust memory or stall the process |

When a semgrep finding from `p/python` does not match a custom rule ID, the
mapper in `stride_rules.py` falls back to keyword heuristics on `rule_id` +
`message`.

---

## 5. Custom Semgrep Rules

Three rules in `semora_custom_rules.yaml` extend `p/python`:

1. **`semora.python.hardcoded-secret`** — Variable names matching
   `(?i)(api_key|secret|password|token|...)` assigned a string literal.
2. **`semora.python.weak-token-generation`** — Security-sensitive variable
   names assigned via `random.<func>(...)`.
3. **`semora.python.sql-injection`** — Variables matching
   `(?i)(query|sql|stmt|...)` constructed from f-strings with interpolation.

---

## 6. Usage — Invoking This Skill

When writing or extending the security node, always:

1. Call `run_semgrep(file_paths, repo_root)` from `semgrep_wrapper.py`.
2. For each raw finding, call `map_to_stride(finding)` from `stride_rules.py`.
3. Call `_classify_severity(finding)` inside `threat_agent.py`.
4. Append the 6-key dict to `state.threat_findings`.

Do **not** add new fields to `RunState` without coordinating with the ADK
Graph Agent (owner of `backend/semora/graph/state.py`).
