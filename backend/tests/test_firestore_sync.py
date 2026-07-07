"""
Verifies the Firestore sync path end to end against the real
semora.sync.firebase_auth / semora.sync.firestore_client modules.

Two things this test deliberately does NOT rely on, because the real
implementation doesn't support them:
  - It never assumes two logged-in sessions can coexist in memory — the real
    session store is a single global file (~/.semora/session.json), so this
    test signs in each test account directly via the Firebase Auth REST API
    instead, independent of that file.
  - It never expects sync_report() to raise on a security-rule denial —
    sync_report() catches all exceptions internally and only prints a
    warning. To actually verify Firestore's rules are enforced, the
    denial-path tests call the Firestore REST API directly.

Requires two throwaway test Firebase accounts and either a real test Firebase
project or the Firestore emulator. Set these in your local .env (never real
production credentials, never committed):
  FIREBASE_WEB_API_KEY / FIREBASE_PROJECT_ID
  FIREBASE_TEST_EMAIL_1 / FIREBASE_TEST_PASSWORD_1
  FIREBASE_TEST_EMAIL_2 / FIREBASE_TEST_PASSWORD_2
"""

import os

import pytest
import requests

from semora.sync import firebase_auth
from semora.sync.firestore_client import serialize_run_state, sync_report

FIREBASE_WEB_API_KEY = os.environ.get("FIREBASE_WEB_API_KEY")
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID")

pytestmark = pytest.mark.skipif(
    not (FIREBASE_WEB_API_KEY and FIREBASE_PROJECT_ID),
    reason="Firebase test project not configured — set FIREBASE_WEB_API_KEY / FIREBASE_PROJECT_ID",
)


def _direct_sign_in(email: str, password: str) -> dict:
    """Sign in via the raw REST endpoint, independent of firebase_auth's
    single global session file, so two accounts can be used side by side
    within one test."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    resp = requests.post(
        url, json={"email": email, "password": password, "returnSecureToken": True}
    )
    resp.raise_for_status()
    return resp.json()  # contains idToken, refreshToken, localId


def _runs_collection_url(uid: str) -> str:
    return (
        f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}"
        f"/databases/(default)/documents/users/{uid}/runs"
    )


@pytest.fixture
def user_one():
    return _direct_sign_in(
        os.environ["FIREBASE_TEST_EMAIL_1"], os.environ["FIREBASE_TEST_PASSWORD_1"]
    )


@pytest.fixture
def user_two():
    return _direct_sign_in(
        os.environ["FIREBASE_TEST_EMAIL_2"], os.environ["FIREBASE_TEST_PASSWORD_2"]
    )


@pytest.fixture
def isolated_session(tmp_path, monkeypatch):
    """Redirect firebase_auth's session file to a temp path for the duration
    of a test, so tests never read or overwrite a developer's real, active
    ~/.semora/session.json."""
    fake_path = tmp_path / "session.json"
    monkeypatch.setattr(firebase_auth, "SESSION_FILE_PATH", str(fake_path))
    return fake_path


def _log_in_as(session_data: dict) -> None:
    """Populate the (already-redirected) session file as if `semora login`
    had just succeeded for this account."""
    firebase_auth._save_session(
        session_data["idToken"], session_data["refreshToken"], session_data["localId"]
    )


SAMPLE_STATE = {
    "repo_path": "/home/dev/projects/auth-service",
    "compliance_score": 91,
    "threat_findings": [],
    "generated_specs": [],
    "execution_results": {},
}


def test_serialize_run_state_maps_fields_for_the_dashboard():
    """Pure unit test, no network — confirms the field mapping and severity
    normalization the dashboard depends on."""
    state = {
        "repo_path": "/home/dev/projects/auth-service",
        "compliance_score": 42,
        "threat_findings": [
            {
                "category": "Information Disclosure",
                "severity": "CRITICAL",
                "file": "auth.py",
                "line": 12,
                "description": "Weak token generator",
                "suggested_patch": "use secrets.token_urlsafe(32)",
            }
        ],
        "generated_specs": ["tests/features/email_verify.feature"],
        "execution_results": {"tests/features/email_verify.feature": {"passed": False}},
    }
    doc = serialize_run_state(state)
    fields = doc["fields"]

    assert fields["repo_name"]["stringValue"] == "auth-service"
    assert fields["compliance_score"]["integerValue"] == "42"

    finding = fields["stride_findings"]["arrayValue"]["values"][0]["mapValue"]["fields"]
    assert finding["severity"]["stringValue"] == "Critical"  # normalized from CRITICAL

    spec = fields["specs"]["arrayValue"]["values"][0]["mapValue"]["fields"]
    assert spec["feature"]["stringValue"] == "email_verify"
    assert spec["covered"]["booleanValue"] is False


def test_sync_report_writes_a_document_the_owner_can_read(isolated_session, user_one):
    _log_in_as(user_one)

    sync_report(SAMPLE_STATE)

    resp = requests.get(
        _runs_collection_url(user_one["localId"]),
        headers={"Authorization": f"Bearer {user_one['idToken']}"},
    )
    resp.raise_for_status()
    documents = resp.json().get("documents", [])
    assert any(
        doc["fields"]["repo_name"]["stringValue"] == "auth-service" for doc in documents
    )


def test_sync_report_skips_gracefully_when_not_logged_in(isolated_session, capsys):
    """isolated_session points at a temp file that doesn't exist yet — this
    simulates a user who has never run `semora login`."""
    sync_report(SAMPLE_STATE)
    captured = capsys.readouterr()
    assert "semora login" in captured.out


def test_cross_user_read_is_denied_by_security_rules(user_one, user_two):
    """The one direct test of whether firestore.rules is actually enforced,
    not just present in the repo. Writes directly via REST (not through
    sync_report) so the assertion is against the real HTTP status, not a
    swallowed exception."""
    doc_data = serialize_run_state(
        {**SAMPLE_STATE, "repo_path": "/home/dev/projects/private-repo"}
    )
    write_resp = requests.post(
        _runs_collection_url(user_one["localId"]),
        headers={"Authorization": f"Bearer {user_one['idToken']}"},
        json=doc_data,
    )
    write_resp.raise_for_status()

    read_resp = requests.get(
        _runs_collection_url(user_one["localId"]),
        headers={"Authorization": f"Bearer {user_two['idToken']}"},
    )
    assert read_resp.status_code == 403


def test_unauthenticated_write_is_denied_by_security_rules(user_one):
    doc_data = serialize_run_state({**SAMPLE_STATE, "repo_path": "/home/dev/projects/x"})
    resp = requests.post(_runs_collection_url(user_one["localId"]), json=doc_data)
    assert resp.status_code in (401, 403)
