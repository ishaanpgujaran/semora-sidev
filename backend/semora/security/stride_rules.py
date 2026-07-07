"""STRIDE Security Rules Module.

Maps each Semgrep finding to exactly one STRIDE category and enriches it with
a short suggested patch.  Also provides the severity classification helper
used by ``threat_agent.py``.

Position in the Semora architecture
-------------------------------------
  threat_node (graph/threat_agent.py)
      └─> audit_security()
              └─> map_to_stride(finding)   ← THIS MODULE
                      └─> returns finding enriched with:
                              category, description, suggested_patch

STRIDE Category Mapping Rationale
----------------------------------
Mapping a vulnerability to a STRIDE category is inherently subjective — the
same bug can threaten more than one property simultaneously.  The convention
used here is: **assign the category that describes the *primary* attack vector
an adversary would use to exploit this vulnerability**, not the downstream
consequence.

Concrete rationale per pattern (also captured in STRIDE_MAPPING below):

  hardcoded-secret (API_KEY = "sk-...")
      → I — Information Disclosure
      Reason: The secret is disclosed *at rest* to any reader of the source
      (colleague, CI system, static analysis tool, future employee).  The
      primary attack is reading the credential from the codebase, not forging
      an identity.  Spoofing is the *downstream* effect; disclosure is the
      *root cause*.

  weak-token-generation (token = random.random())
      → S — Spoofing
      Reason: A non-CSPRNG token is predictable.  The primary attack is
      *guessing* or *brute-forcing* the token value to forge a session and
      impersonate a legitimate user.  The token is not disclosed — it is
      forged, which maps directly to Spoofing.

  sql-injection (query = f"SELECT … {user_id}")
      → T — Tampering
      Reason: User-controlled input is injected into a SQL statement.  The
      adversary's primary capability is to *modify* (INSERT, UPDATE, DELETE)
      or *exfiltrate* data beyond what the application intends, i.e. tampering
      with the data layer.  We choose Tampering over Information Disclosure
      because the injection gives *write* capability, not only *read*.

  eval / exec with user input
      → E — Elevation of Privilege
      Reason: Arbitrary code execution grants the attacker the process's full
      privilege level, bypassing any application-level access control.

  bare except: / exception swallow
      → R — Repudiation
      Reason: Swallowing exceptions destroys the error audit trail.  An
      attacker exploiting a silent failure path can claim the action never
      happened, making the attack non-attributable (repudiation).

  path traversal / unbounded file reads
      → D — Denial of Service
      Reason: Reading attacker-controlled paths (e.g. /dev/zero, large binary
      files) can exhaust memory or stall I/O, degrading service availability.

  default (unrecognised rule)
      → I — Information Disclosure
      Reason: Most unclassified security smells ultimately expose some
      information that should remain private.  Defaulting to I is conservative
      and errs on the side of caution.
"""

from typing import Any

# ---------------------------------------------------------------------------
# Rule ID normalisation
# ---------------------------------------------------------------------------
#
# When semgrep is invoked with ``--config path/to/rules.yaml``, it prefixes
# each rule's ID with a dotted version of the YAML file path.  For example,
# if the YAML lives at ``backend/semora/security/semora_custom_rules.yaml``
# and defines ``semora.python.hardcoded-secret``, the check_id in the JSON
# output becomes:
#
#   backend.semora.security.semora.python.hardcoded-secret
#
# We strip that prefix so the STRIDE_MAPPING exact-match keys remain stable
# regardless of where in the filesystem the package is installed.

_SEMORA_RULE_PREFIX: str = "semora.python."


def _normalize_rule_id(rule_id: str) -> str:
    """Strip the file-path namespace that semgrep prepends to local YAML rule IDs.

    Args:
        rule_id: The raw ``check_id`` string from semgrep's JSON output.

    Returns:
        The normalised rule ID beginning with ``semora.python.`` if it is one
        of our custom rules, or the original string otherwise.

    Examples::

        >>> _normalize_rule_id("backend.semora.security.semora.python.hardcoded-secret")
        'semora.python.hardcoded-secret'
        >>> _normalize_rule_id("python.lang.security.audit.eval-detected.eval-detected")
        'python.lang.security.audit.eval-detected.eval-detected'
    """
    idx = rule_id.find(_SEMORA_RULE_PREFIX)
    if idx != -1:
        return rule_id[idx:]
    return rule_id

# ---------------------------------------------------------------------------
# Exact-match lookup: custom Semora rule IDs → (STRIDE category, suggested patch)
# ---------------------------------------------------------------------------
#
# Key   : the full Semgrep rule ID string (check_id field in JSON output)
# Value : 2-tuple of (STRIDE_CATEGORY_STRING, SHORT_PATCH_SUGGESTION)
#
# For Semora's own rules the mapping is authoritative and deterministic.
# For third-party p/python rules we fall through to keyword heuristics below.

STRIDE_MAPPING: dict[str, tuple[str, str]] = {
    # ------------------------------------------------------------------
    # semora.python.hardcoded-secret
    # STRIDE: I — Information Disclosure
    # Rationale: secret baked into source is disclosed to any reader.
    # ------------------------------------------------------------------
    "semora.python.hardcoded-secret": (
        "I — Information Disclosure",
        "Replace the literal value with os.getenv('VAR_NAME') and add VAR_NAME "
        "to your .env file (loaded via python-dotenv). Never commit secrets.",
    ),

    # ------------------------------------------------------------------
    # semora.python.weak-token-generation
    # STRIDE: S — Spoofing
    # Rationale: predictable token can be guessed/forged to impersonate a user.
    # ------------------------------------------------------------------
    "semora.python.weak-token-generation": (
        "S — Spoofing",
        "Replace random.<func>() with secrets.token_hex(32) or "
        "secrets.token_urlsafe(32) from the standard library 'secrets' module.",
    ),

    # ------------------------------------------------------------------
    # semora.python.sql-injection
    # STRIDE: T — Tampering
    # Rationale: attacker modifies the SQL intent, altering the data layer.
    # ------------------------------------------------------------------
    "semora.python.sql-injection": (
        "T — Tampering",
        "Use parameterised queries: cursor.execute('SELECT … WHERE id = %s', (user_id,)) "
        "instead of string interpolation.",
    ),
}

# ---------------------------------------------------------------------------
# Keyword heuristics for third-party p/python rule IDs
# ---------------------------------------------------------------------------
#
# p/python rule IDs follow the pattern:
#   python.<framework>.security.<category>.<rule-name>
#
# We match substrings in the lowercased rule_id and message to assign a
# category.  Order matters — more-specific patterns are checked first.

_KEYWORD_MAP: list[tuple[list[str], str, str]] = [
    # Elevation of Privilege — arbitrary code execution patterns
    (
        ["eval", "exec", "code-injection", "command-injection", "subprocess-shell",
         "rce", "arbitrary-code"],
        "E — Elevation of Privilege",
        "Avoid eval()/exec() with user-controlled input. Use a safe AST parser "
        "or a whitelist of allowed operations.",
    ),
    # Tampering — data manipulation via injection
    (
        ["sql", "inject", "tainted-sql", "formatted-sql", "nosql",
         "ldap", "xpath"],
        "T — Tampering",
        "Use parameterised queries or ORM methods instead of string concatenation.",
    ),
    # Spoofing — weak or predictable authentication material
    (
        ["weak-random", "predictable", "insecure-random", "md5", "sha1",
         "weak-hash", "hardcoded-password-default"],
        "S — Spoofing",
        "Use secrets.token_hex(32) or hashlib.sha256 / bcrypt for auth material.",
    ),
    # Information Disclosure — credential / secret exposure
    (
        ["hardcoded", "secret", "password", "credential", "api-key",
         "private-key", "token", "auth"],
        "I — Information Disclosure",
        "Load secrets from environment variables; never hardcode credentials.",
    ),
    # Repudiation — audit trail destruction
    (
        ["except", "bare-except", "broad-except", "swallow", "suppress",
         "logging", "repudiat"],
        "R — Repudiation",
        "Use specific exception types (except ValueError:) and log all exceptions "
        "at an appropriate level before re-raising or handling.",
    ),
    # Denial of Service — resource exhaustion
    (
        ["dos", "denial", "flood", "resource", "memory", "timeout",
         "traversal", "path-injection", "zip-bomb", "regex"],
        "D — Denial of Service",
        "Validate and sanitise all user-supplied paths/sizes before I/O operations.",
    ),
]


def _infer_stride_category(
    rule_id: str, message: str
) -> tuple[str, str]:
    """Infer the STRIDE category from a rule_id and message using keyword matching.

    Args:
        rule_id: The Semgrep check_id string.
        message: The human-readable message from the Semgrep finding.

    Returns:
        A 2-tuple of (STRIDE_CATEGORY_STRING, SHORT_PATCH_SUGGESTION).
    """
    haystack = (rule_id + " " + message).lower()

    for keywords, category, patch in _KEYWORD_MAP:
        if any(kw in haystack for kw in keywords):
            return category, patch

    # Default: when a rule doesn't match any keyword, treat it as a potential
    # information disclosure — conservative but rarely wrong.
    return (
        "I — Information Disclosure",
        "Review this finding manually and apply the principle of least privilege.",
    )


def map_to_stride(finding: dict[str, Any]) -> dict[str, Any]:
    """Enrich a normalised Semgrep finding with STRIDE category and suggested patch.

    Looks up the finding's ``rule_id`` in ``STRIDE_MAPPING`` first (exact match
    for Semora's own custom rules).  If not found, falls back to keyword
    heuristics via ``_infer_stride_category``.

    Args:
        finding: A normalised finding dict as returned by ``run_semgrep``,
            with keys: ``rule_id``, ``file``, ``line``, ``message``, ``severity``.

    Returns:
        The original finding dict augmented with two new keys:

        * ``category``       — the STRIDE category string
        * ``suggested_patch`` — a short inline code suggestion
        * ``description``    — a human-readable description of the threat
          (combines the rule message with the STRIDE category context)
    """
    rule_id: str = _normalize_rule_id(finding.get("rule_id", ""))
    message: str = finding.get("message", "")

    if rule_id in STRIDE_MAPPING:
        category, suggested_patch = STRIDE_MAPPING[rule_id]
    else:
        category, suggested_patch = _infer_stride_category(rule_id, message)

    enriched = dict(finding)
    enriched["category"] = category
    enriched["suggested_patch"] = suggested_patch
    enriched["description"] = (
        f"[{category}] {message}" if message else
        f"[{category}] Security finding from rule '{rule_id}'."
    )

    return enriched
