"""
Firestore Client for Semora.
Handles syncing RunState reports to Firebase via REST API.
"""

import os
import time
import requests
from typing import Any, Dict, Union
from dotenv import load_dotenv

from backend.semora.graph.state import RunState
from backend.semora.sync.firebase_auth import get_valid_id_token, _load_session

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

def serialize_run_state(state: Union[RunState, dict]) -> Dict[str, Any]:
    """Converts a RunState into a Firestore REST Document format."""
    is_pydantic = not isinstance(state, dict)
    
    if is_pydantic:
        if hasattr(state, "model_dump"):
            data = state.model_dump()
        else:
            data = getattr(state, "dict", lambda: dict(state.__dict__))()
    else:
        data = dict(state)
        
    # Inject timestamp so the dashboard can sort them
    data["timestamp"] = int(time.time())
    
    fields = {}
    for k, v in data.items():
        fields[k] = _to_firestore_value(v)
        
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
