from pydantic import BaseModel
from typing import Optional, List

class TallyStockGroup(BaseModel):
    guid: Optional[str] = None
    name: str
    parent_group: Optional[str] = "Primary"
    series_code: Optional[str] = None

class TallyStockItem(BaseModel):
    guid: Optional[str] = None
    name: str
    parent_group: Optional[str] = "Primary"
    part_number: str
    closing_balance: float = 0.0
    closing_rate: float = 0.0
    closing_value: float = 0.0
    purchase_pending: float = 0.0
    sales_due: float = 0.0
    nett_available: float = 0.0
    reorder_level: float = 0.0
    shortfall: float = 0.0

class StockSyncResponse(BaseModel):
    status: str
    total_records: int
    items: List[TallyStockItem]
    sync_timestamp: str
