"""
Email verification routes for the sample target app.

NOTE FOR THE TEAM: this file is intentionally written the way a fast "vibe
coding" prompt would produce it — it works, but it's missing input validation
and uses a predictable token generator. This is the fixture Semora's demo
video and Agent 8's end-to-end test both rely on. Do not "fix" this file
directly; the fix should happen live, during the demo, by prompting
Antigravity with the patch Semora suggests (see SEMORA_MASTER_PLAN.md
Section 9 for the exact suggested patch).
"""

import random

from fastapi import APIRouter

router = APIRouter()

# In-memory store standing in for a real database, for demo purposes only.
_pending_tokens: dict[str, str] = {}


def generate_verification_token() -> str:
    """Generate a token for an email verification link.

    NOTE: random.random() is not cryptographically secure — it's
    predictable, which is exactly the CRITICAL finding Semora's STRIDE
    agent should catch here (Information Disclosure: token can be guessed).
    """
    return str(random.random())


@router.post("/request-verification")
def request_verification(email: str):
    """Issue a verification token for the given email address.

    NOTE: no validation on `email` at all — an empty string, a malformed
    address, or unexpected input all pass straight through. This is the gap
    Semora's Spec Agent should generate adversarial test cases for.
    """
    token = generate_verification_token()
    _pending_tokens[email] = token
    return {"message": "Verification email sent", "email": email}


@router.post("/verify")
def verify_email(email: str, token: str):
    """Confirm an email address using its verification token."""
    expected = _pending_tokens.get(email)
    if expected == token:
        return {"verified": True}
    return {"verified": False}
