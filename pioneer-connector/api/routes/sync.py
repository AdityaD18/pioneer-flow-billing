from fastapi import APIRouter, Query
from services.sync_engine import SyncEngine

router = APIRouter(prefix="/sync", tags=["Tally Synchronization Engine"])

@router.post("/trigger")
def trigger_sync(sync_type: str = Query("full", description="Type of synchronization: 'full' or 'incremental'")):
    """
    Triggers Tally synchronization engine (Download -> Validate -> Stage -> Commit -> Manifest).
    Executes retries on failure and rolls back SQLite cache on errors.
    """
    return SyncEngine.execute_sync(sync_type=sync_type)

@router.get("/status")
def get_sync_status():
    """Retrieves statistics and manifest metadata for the last synchronization run."""
    return SyncEngine.get_sync_status()
