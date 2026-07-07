"""Deliberately vulnerable sample file — used exclusively as a test fixture.

THIS FILE CONTAINS INTENTIONAL SECURITY VULNERABILITIES.
It exists solely to validate that the Semora STRIDE threat modeler correctly
detects and classifies the following patterns:

  1. Hardcoded API key   → I — Information Disclosure  (CRITICAL)
  2. SQL injection       → T — Tampering               (CRITICAL)

DO NOT import or use this file in production code.
"""

# -------------------------------------------------------------------------
# Vulnerability 1: Hardcoded API key
# STRIDE: I — Information Disclosure
# Severity: CRITICAL
#
# A secret is baked directly into source.  Anyone with read access to the
# repository — or any CI log that prints locals() — can retrieve the key.
# -------------------------------------------------------------------------
API_KEY = "sk-abc123examplekeyIsLongEnoughToTriggerRule"


def get_api_key() -> str:
    """Return the (insecurely hardcoded) API key."""
    return API_KEY


# -------------------------------------------------------------------------
# Vulnerability 2: SQL injection via f-string interpolation
# STRIDE: T — Tampering
# Severity: CRITICAL
#
# The variable `query` is named to look like a SQL query (matches our custom
# rule's metavariable-regex) and is built using an f-string that directly
# interpolates `user_id` without any parameterisation.  An attacker can
# supply a value like `1 OR 1=1` to exfiltrate or modify arbitrary data.
# -------------------------------------------------------------------------
def get_user(user_id: int) -> str:
    """Fetch a user record using a dangerously interpolated SQL query.

    Args:
        user_id: The user identifier — NOT safely parameterised.

    Returns:
        The raw SQL query string (for demonstration purposes only).
    """
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return query
