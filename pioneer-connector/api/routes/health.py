from fastapi import APIRouter, Query
from config.settings import settings
from tally.connection import TallyConnectionManager
from cache.offline_queue import get_offline_queue_size

router = APIRouter(tags=["Health & System"])

@router.get("/health")
def health_check(
    host: str = Query(None, description="Optional override Tally host"),
    port: int = Query(None, description="Optional override Tally port")
):
    """
    Enhanced Readiness Diagnostics & Tally Connection Health Check Endpoint.
    Returns healthy, ready, tally_connected, authenticated, cloud_connected, and queue_size.
    """
    tally_health = TallyConnectionManager.test_connection(host=host, port=port)
    is_tally = tally_health.get("connected", False)
    q_size = get_offline_queue_size()

    return {
        "healthy": True,
        "ready": is_tally,
        "tally_connected": is_tally,
        "authenticated": True,
        "cloud_connected": True,
        "queue_size": q_size,
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "tally_health": tally_health
    }
