from typing import Dict, Any, List, Optional
from app.models.domain import Customer

class CustomerMapper:
    """Converts Connector REST customer JSON payloads into canonical Customer domain models."""

    @staticmethod
    def to_domain(json_dict: Dict[str, Any], index: int = 1) -> Customer:
        return Customer(
            id=index,
            name=json_dict.get("name", ""),
            discount_percentage=float(json_dict.get("discount_percentage", 0.0)),
            gst_number=json_dict.get("gstin") or "",
            payment_terms=json_dict.get("payment_terms") or "Net 30 Days"
        )

    @staticmethod
    def to_domain_list(customers_json: List[Dict[str, Any]], search_query: Optional[str] = None) -> List[Customer]:
        customers = []
        for idx, raw in enumerate(customers_json, start=1):
            c_name = raw.get("name", "")
            if search_query and search_query.lower() not in c_name.lower():
                continue
            customers.append(CustomerMapper.to_domain(raw, index=idx))
        return customers
