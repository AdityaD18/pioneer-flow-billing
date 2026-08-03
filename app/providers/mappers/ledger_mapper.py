from typing import Dict, Any, List
from app.models.domain import Ledger

class LedgerMapper:
    """Converts Connector REST ledger JSON payloads into canonical Ledger domain models."""

    @staticmethod
    def to_domain(json_dict: Dict[str, Any], index: int = 1) -> Ledger:
        return Ledger(
            id=index,
            name=json_dict.get("name", ""),
            reference_number=json_dict.get("guid") or f"LEDG-{index:04d}",
            customer_name=json_dict.get("name", ""),
            date=json_dict.get("updated_at", "")[:10] or "2026-01-01",
            grand_total=float(json_dict.get("closing_balance", 0.0)),
            type=json_dict.get("ledger_type", "General").title()
        )

    @staticmethod
    def to_domain_list(ledgers_json: List[Dict[str, Any]]) -> List[Ledger]:
        return [LedgerMapper.to_domain(raw, index=idx) for idx, raw in enumerate(ledgers_json, start=1)]
