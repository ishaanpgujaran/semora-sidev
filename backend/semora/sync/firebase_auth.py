"""
Firebase Authentication module for Semora.
Handles user sign-in, sign-up, and token refresh using Firebase Auth REST API.
"""
import os
import json
import time
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Ensure .env is loaded
load_dotenv()

# We store the session in the user's home directory.
# SECURITY NOTE: This path is ~/.semora/session.json. It lives in the user's home 
# directory, outside of any target repository. Therefore, it is naturally safe 
# from being accidentally committed to version control when a user commits code 
# in their project repository.
SESSION_FILE_PATH = os.path.expanduser("~/.semora/session.json")

def get_firebase_api_key() -> str:
    """Helper to get the API key to avoid evaluating it on module load if missing."""
    key = os.getenv("FIREBASE_WEB_API_KEY")
    if not key:
        raise ValueError("FIREBASE_WEB_API_KEY environment variable is not set.")
    return key

def _save_session(id_token: str, refresh_token: str, local_id: str) -> None:
    os.makedirs(os.path.dirname(SESSION_FILE_PATH), exist_ok=True)
    session_data = {
        "idToken": id_token,
        "refreshToken": refresh_token,
        "localId": local_id,
        "timestamp": time.time()
    }
    with open(SESSION_FILE_PATH, "w") as f:
        json.dump(session_data, f)

def _load_session() -> Optional[Dict[str, Any]]:
    if not os.path.exists(SESSION_FILE_PATH):
        return None
    try:
        with open(SESSION_FILE_PATH, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return None

def login_command(email: str, password: str) -> None:
    """Handles the CLI login command."""
    api_key = get_firebase_api_key()

    # 1. Attempt Sign-In
    signin_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    
    response = requests.post(signin_url, json=payload)
    data = response.json()
    
    if response.status_code == 200:
        _save_session(data["idToken"], data["refreshToken"], data["localId"])
        print("Successfully signed in.")
        return

    # Check if failed because account doesn't exist
    error_message = data.get("error", {}).get("message", "")
    if error_message == "EMAIL_NOT_FOUND":
        print("Account not found. Attempting to create one...")
        
        # 2. Attempt Sign-Up
        signup_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={api_key}"
        signup_response = requests.post(signup_url, json=payload)
        signup_data = signup_response.json()
        
        if signup_response.status_code == 200:
            _save_session(signup_data["idToken"], signup_data["refreshToken"], signup_data["localId"])
            print("Successfully created account and signed in.")
        else:
            print(f"Failed to create account: {signup_data.get('error', {}).get('message')}")
    else:
        print(f"Sign-in failed: {error_message}")

def get_valid_id_token() -> Optional[str]:
    """
    Returns a valid ID token. If the stored token is older than 55 minutes,
    uses the refresh token to get a new one before returning it.
    """
    session = _load_session()
    if not session:
        return None
        
    current_time = time.time()
    # 55 minutes in seconds
    if (current_time - session.get("timestamp", 0)) > (55 * 60):
        api_key = get_firebase_api_key()
            
        refresh_url = f"https://securetoken.googleapis.com/v1/token?key={api_key}"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": session["refreshToken"]
        }
        
        response = requests.post(refresh_url, json=payload)
        data = response.json()
        
        if response.status_code == 200:
            # Update session with new tokens
            new_id_token = data["id_token"]
            new_refresh_token = data["refresh_token"]
            local_id = data["user_id"]
            
            _save_session(new_id_token, new_refresh_token, local_id)
            return new_id_token
        else:
            print(f"Failed to refresh token: {data.get('error', {}).get('message')}")
            return None
            
    return session["idToken"]
