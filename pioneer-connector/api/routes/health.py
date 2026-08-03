from fastapi import APIRouter, Query
from config.settings import settings
from tally.connection import TallyConnectionManager

router = APIRouter(tags=["Health & System"])

@router.get("/health")
def health_check(
    host: str = Query(None, description="Optional override Tally host"),
    port: int = Query(None, description="Optional override Tally port")
):
    """
    Tally Connection Health Check Endpoint.
    Probes TallyPrime XML server, detects active company & version, and measures latency.
    """
    tally_health = TallyConnectionManager.test_connection(host=host, port=port)
    return {
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "tally_health": tally_health
    }

@router.get("/api/v1/health/tally")
def tally_health_detail(
    host: str = Query(None, description="Optional override Tally host"),
    port: int = Query(None, description="Optional override Tally port")
):
    """Detailed TallyPrime XML HTTP status endpoint."""
    return TallyConnectionManager.test_connection(host=host, port=port)
