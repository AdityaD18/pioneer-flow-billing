from pydantic import BaseModel
from typing import Optional

class TallyLedger(BaseModel):
    guid: Optional[str] = None
    name: str
    parent_group: Optional[str] = None
    closing_balance: float = 0.0
    gstin: Optional[str] = None
