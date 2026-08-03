from pydantic import BaseModel
from typing import Optional, List

class TallyLedger(BaseModel):
    guid: Optional[str] = None
    name: str
    parent_group: str = "Primary"
    ledger_type: str = "general" # customer | supplier | expense | income | tax | general
    closing_balance: float = 0.0
    gstin: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    state: Optional[str] = None
    pin_code: Optional[str] = None

class LedgerSyncResponse(BaseModel):
    status: str
    total_records: int
    ledgers: List[TallyLedger]
    sync_timestamp: str
