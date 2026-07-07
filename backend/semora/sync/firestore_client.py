"""
Firestore Client for Semora.
Handles syncing RunState reports to Firebase via REST API.
"""

import os
import time
import requests
from typing import Any, Dict, Union
from dotenv import load_dotenv

from semora.graph.state import RunState
from semora.sync.firebase_auth import get_valid_id_token, _load_session

# Ensure .env is loaded
load_dotenv()

def _to_firestore_value(data: Any) -> Dict[str, Any]:
    """Helper to convert standard Python types to Firestore REST types."""
    if isinstance(data, dict):
        return {"mapValue": {"fields": {str(k): _to_firestore_value(v) for k, v in data.items()}}}
    elif isinstance(data, list) or isinstance(data, tuple):
        return {"arrayValue": {"values": [_to_firestore_value(v) for v in data]}}
    elif isinstance(data, bool):
        return {"booleanValue": data}
    elif isinstance(data, int):
        return {"integerValue": str(data)}
    elif isinstance(data, float):
        return {"doubleValue": data}
    elif data is None:
        return {"nullValue": None}
    else:
        return {"stringValue": str(data)}

def _normalize_severity(sev: str) -> str:
    """Convert backend severity strings to title case for the frontend.

    Backend uses: CRITICAL, HIGH, WARNING
    Frontend expects: Critical, High, Medium, Low
    """
    mapping = {
        "CRITICAL": "Critical",
        "HIGH": "High",
        "WARNING": "Medium",
    }
    return mapping.get(sev.upper(), sev.title()) if sev else "Medium"


def _get_commit_sha(repo_path: str) -> str:
    """Get the current HEAD commit SHA, or empty string if unavailable."""
    try:
        import git
        repo = git.Repo(repo_path, search_parent_directories=True)
        return str(repo.head.commit.hexsha)
    except Exception:
        return ""


def serialize_run_state(state: Union[RunState, dict]) -> Dict[str, Any]:
    """Converts a RunState into a Firestore REST Document format.

    The output fields are aligned with what the React dashboard expects:
      - repo_name    (str)  — basename of repo_path
      - commit_sha   (str)  — HEAD commit SHA
      - compliance_score (int)
      - stride_findings  (list) — renamed from threat_findings, title-case severity
      - specs        (list) — structured [{feature, file, covered}]
      - timestamp    (Firestore Timestamp via timestampValue)
    """
    is_pydantic = not isinstance(state, dict)

    if is_pydantic:
        if hasattr(state, "model_dump"):
            data = state.model_dump()
        else:
            data = getattr(state, "dict", lambda: dict(state.__dict__))()
    else:
        data = dict(state)

    repo_path = data.get("repo_path", "")

    # Build the dashboard-friendly document
    doc: Dict[str, Any] = {}

    # repo_name: basename of the repo path
    doc["repo_name"] = os.path.basename(os.path.abspath(repo_path)) if repo_path else "unknown"

    # commit_sha
    doc["commit_sha"] = _get_commit_sha(repo_path)

    # compliance_score
    doc["compliance_score"] = data.get("compliance_score", 0) or 0

    # stride_findings: renamed from threat_findings, with title-case severity
    raw_findings = data.get("threat_findings", [])
    doc["stride_findings"] = [
        {
            "category": f.get("category", ""),
            "severity": _normalize_severity(f.get("severity", "")),
            "file": f.get("file", ""),
            "line": f.get("line", 0),
            "description": f.get("description", ""),
            "suggested_patch": f.get("suggested_patch", ""),
        }
        for f in raw_findings
    ]

    # specs: transform flat file paths into structured objects for SpecMatrix
    execution_results = data.get("execution_results", {})
    generated_specs = data.get("generated_specs", [])
    doc["specs"] = [
        {
            "feature": os.path.splitext(os.path.basename(spec_path))[0],
            "file": spec_path,
            "covered": bool(
                execution_results.get(spec_path, {}).get("passed", False)
            ) if isinstance(execution_results.get(spec_path), dict) else False,
        }
        for spec_path in generated_specs
    ]

    # execution_results (keep for detail views)
    doc["execution_results"] = execution_results

    # timestamp: Firestore timestampValue (ISO 8601)
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build Firestore REST fields
    fields: Dict[str, Any] = {}
    for k, v in doc.items():
        fields[k] = _to_firestore_value(v)

    # Override timestamp to use Firestore's native timestampValue
    fields["timestamp"] = {"timestampValue": now_iso}

    return {"fields": fields}

def sync_report(state: Union[RunState, dict]) -> None:
    """Syncs the given RunState to Firestore under the current user's profile."""
    try:
        session = _load_session()
        if not session or not session.get("localId"):
            print("Run `semora login` to sync results to your dashboard")
            return
            
        uid = session["localId"]
        
        # This automatically handles token refresh if needed
        id_token = get_valid_id_token()
        if not id_token:
            print("Run `semora login` to sync results to your dashboard")
            return
            
        project_id = os.getenv("FIREBASE_PROJECT_ID")
        if not project_id:
            # If project ID isn't configured, we can't sync, but we shouldn't fail.
            print("Warning: FIREBASE_PROJECT_ID is not set in .env. Skipping sync.")
            return
            
        doc_data = serialize_run_state(state)
        
        # Firestore REST API endpoint for POST (auto-generates document ID)
        url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/users/{uid}/runs"
        
        headers = {
            "Authorization": f"Bearer {id_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers, json=doc_data)
        
        # Accept 200 OK or 201 Created
        if response.status_code not in (200, 201):
            print(f"Warning: Failed to sync report to Firestore. (Status: {response.status_code})")
            
    except Exception:
        # Silently catch exceptions to ensure terminal output/commit checks always work
        print("Warning: Exception occurred while syncing report. Skipping sync.")
