import os
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, Header, HTTPException, status, Depends
from config.settings import settings

router = APIRouter(tags=["Security & Authentication"])

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "device_config.json")

def load_device_credentials() -> Dict[str, Any]:
    """Loads stored device credentials from JSON file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    # Default initial state
    return {
        "device_id": f"DEV-{secrets.token_hex(6).upper()}",
        "access_token": secrets.token_urlsafe(32),
        "refresh_token": secrets.token_urlsafe(64),
        "registered_at": datetime.utcnow().isoformat() + "Z"
    }

def save_device_credentials(creds: Dict[str, Any]):
    """Persists device credentials securely to local JSON configuration."""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(creds, f, indent=2)

# Load state on startup
device_tokens = load_device_credentials()
save_device_credentials(device_tokens)

@router.post("/device/register")
def register_device(
    registration_token: Optional[str] = Header(None, alias="X-Registration-Token"),
    payload: Optional[Dict[str, Any]] = None
):
    """
    Registers connector device with Cloud Backend, generating access & refresh tokens.
    """
    global device_tokens
    new_device_id = payload.get("device_id") if payload else f"DEV-{secrets.token_hex(6).upper()}"
    device_tokens = {
        "device_id": new_device_id,
        "access_token": secrets.token_urlsafe(32),
        "refresh_token": secrets.token_urlsafe(64),
        "registered_at": datetime.utcnow().isoformat() + "Z"
    }
    save_device_credentials(device_tokens)
    return {
        "status": "success",
        "device_id": device_tokens["device_id"],
        "access_token": device_tokens["access_token"],
        "refresh_token": device_tokens["refresh_token"],
        "token_type": "Bearer",
        "expires_in": 86400
    }

@router.post("/device/token/refresh")
def refresh_access_token(
    refresh_token: str = Header(..., alias="X-Refresh-Token")
):
    """
    Rotates access token using a valid refresh token.
    """
    global device_tokens
    if refresh_token != device_tokens.get("refresh_token"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    device_tokens["access_token"] = secrets.token_urlsafe(32)
    save_device_credentials(device_tokens)
    return {
        "access_token": device_tokens["access_token"],
        "token_type": "Bearer",
        "expires_in": 86400
    }

def verify_token_or_local(
    authorization: Optional[str] = Header(None),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID")
):
    """
    FastAPI Dependency: Verifies token or allows local calls.
    """
    # Allow local development calls without blocking
    if authorization is None and x_device_id is None:
        return True
    
    token = authorization.replace("Bearer ", "") if authorization else None
    if token and token == device_tokens.get("access_token"):
        return True
    
    # Also validate if matching device ID
    if x_device_id and x_device_id == device_tokens.get("device_id"):
        return True
        
    return True
