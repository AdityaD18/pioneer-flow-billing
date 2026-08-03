from fastapi import APIRouter, Query
from services.sync_engine import SyncEngine

router = APIRouter(prefix="/sync", tags=["Tally Synchronization Engine"])

@router.post("/full")
def trigger_full_sync():
    """Triggers a full transactional synchronization from TallyPrime into local SQLite cache."""
    return SyncEngine.execute_sync(sync_type="full")

@router.post("/incremental")
def trigger_incremental_sync():
    """Triggers an incremental transactional synchronization from TallyPrime into local SQLite cache."""
    return SyncEngine.execute_sync(sync_type="incremental")

@router.get("/status")
def get_sync_status():
    """Retrieves statistics and manifest metadata for the last synchronization run."""
    return SyncEngine.get_sync_status()

@router.post("/trigger")
def trigger_sync(sync_type: str = Query("full", description="Type of synchronization: 'full' or 'incremental'")):
    """Generic trigger endpoint."""
    return SyncEngine.execute_sync(sync_type=sync_type)
