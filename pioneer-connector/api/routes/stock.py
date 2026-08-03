from fastapi import APIRouter, HTTPException, Query
from typing import List
from services.stock_service import StockService
from tally.models.stock import TallyStockItem, TallyStockGroup, StockSyncResponse

router = APIRouter(prefix="/stock", tags=["Stock Inventory Synchronization"])

@router.get("", response_model=StockSyncResponse)
def get_all_stock(force_refresh: bool = Query(False, description="Force live sync from Tally")):
    """
    Downloads and retrieves all stock items from Tally in canonical JSON format.
    Exposes zero XML.
    """
    items = StockService.sync_stock_items(force_refresh=force_refresh)
    return StockSyncResponse(
        status="success",
        total_records=len(items),
        items=items,
        sync_timestamp=StockService.get_last_sync_timestamp()
    )

@router.get("/groups", response_model=List[TallyStockGroup])
def get_stock_groups(force_refresh: bool = Query(False, description="Force live sync from Tally")):
    """Retrieves all stock groups from Tally in JSON format."""
    return StockService.sync_stock_groups(force_refresh=force_refresh)

@router.get("/{item_id}", response_model=TallyStockItem)
def get_stock_item_by_id(item_id: str):
    """Retrieves a single stock item by part number, name, or GUID."""
    item = StockService.get_stock_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Stock item '{item_id}' not found.")
    return item
