from pydantic import BaseModel
from typing import Optional

class TallyStockItem(BaseModel):
    guid: Optional[str] = None
    name: str
    parent_group: Optional[str] = None
    part_number: Optional[str] = None
    closing_balance: float = 0.0
    closing_rate: float = 0.0
    closing_value: float = 0.0
