from fastapi import APIRouter

router = APIRouter(prefix="/sync", tags=["Tally Synchronization"])

@router.post("/trigger")
def trigger_sync():
    return {
        "status": "initiated",
        "message": "Tally synchronization pipeline architecture ready."
    }
