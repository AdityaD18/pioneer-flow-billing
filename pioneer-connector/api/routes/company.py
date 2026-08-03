from fastapi import APIRouter
from config.settings import settings
from tally.connection import TallyConnectionManager

router = APIRouter(tags=["Company Details"])

@router.get("/company")
def get_active_company():
    """
    Retrieves active Tally company profile and system metadata in stable JSON format.
    """
    conn_info = TallyConnectionManager.test_connection()
    return {
        "company_name": conn_info.get("company_name") or settings.TALLY_COMPANY,
        "tally_version": conn_info.get("tally_version") or "TallyPrime 7.1",
        "connected": conn_info.get("connected", False),
        "endpoint": f"http://{settings.TALLY_HOST}:{settings.TALLY_PORT}",
        "currency": "INR",
        "gstin": "27AAACP1234F1Z9" # Pioneer Automation default
    }
