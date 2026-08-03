from fastapi import APIRouter
from config.settings import settings

router = APIRouter(tags=["Health & System"])

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "tally_target": f"http://{settings.TALLY_HOST}:{settings.TALLY_PORT}"
    }
