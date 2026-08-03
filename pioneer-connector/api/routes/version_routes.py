import os
import platform
import getpass
from datetime import datetime
from fastapi import APIRouter
from config.settings import settings
from tally.connection import TallyConnectionManager

router = APIRouter(tags=["System Version & Identity"])

@router.get("/version")
def get_version():
    """
    Returns protocol version, connector build version, and build date.
    """
    return {
        "version": "2.0.1",
        "build": "2026.08.03",
        "protocol": 1,
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV
    }

@router.get("/capabilities")
def get_capabilities():
    """
    Exposes functional capability flags to Cloud ERP.
    """
    return {
        "stock": True,
        "ledgers": True,
        "customers": True,
        "suppliers": True,
        "incremental_sync": True,
        "company_switch": True,
        "offline_queue": True
    }

@router.get("/identity")
def get_identity():
    """
    Returns unique machine, device, OS, user, and active Tally identity info.
    """
    conn_info = TallyConnectionManager.test_connection()
    device_id = getattr(settings, "DEVICE_ID", None) or f"DEV-{platform.node()}"
    
    return {
        "device_id": device_id,
        "company_guid": conn_info.get("company_guid", "N/A"),
        "company_name": conn_info.get("company_name", "N/A"),
        "computer_name": platform.node(),
        "connector_version": "2.0.1",
        "last_sync": conn_info.get("last_checked", datetime.utcnow().isoformat() + "Z"),
        "tally_version": conn_info.get("tally_version", "N/A"),
        "windows_user": getpass.getuser(),
        "os_platform": platform.platform()
    }
