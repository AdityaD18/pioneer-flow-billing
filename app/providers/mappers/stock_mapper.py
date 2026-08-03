from typing import Dict, Any, List, Optional
from app.models.domain import StockItem, StockGroup, PurchaseOrder, SalesOrder
from app.core.config import Config

class StockMapper:
    """Converts Connector REST stock JSON payloads into canonical StockItem & StockGroup domain models."""

    @staticmethod
    def to_domain(json_dict: Dict[str, Any]) -> StockItem:
        p_num = json_dict.get("part_number") or json_dict.get("name", "")
        p_series = json_dict.get("parent_group") or "General"
        
        return StockItem(
            product_id=json_dict.get("guid") or hash(p_num),
            part_number=p_num,
            series=p_series,
            make=Config.DEFAULT_MAKE,
            packing_quantity=100,
            current_stock=float(json_dict.get("closing_balance", 0.0)),
            cost_price_100=float(json_dict.get("closing_rate", 0.0)) * 100.0,
            rate_per_unit=float(json_dict.get("closing_rate", 0.0))
        )

    @staticmethod
    def to_domain_list(items_json: List[Dict[str, Any]], search_kw: Optional[str] = None, series: Optional[str] = None) -> List[StockItem]:
        items = []
        for raw in items_json:
            p_num = raw.get("part_number") or raw.get("name", "")
            p_series = raw.get("parent_group") or "General"

            if search_kw:
                skw = search_kw.lower()
                if skw not in p_num.lower() and skw not in raw.get("name", "").lower():
                    continue
            if series and series != "All Series":
                if p_series != series and f"Series {series}" != series:
                    continue

            items.append(StockMapper.to_domain(raw))
        return items

    @staticmethod
    def group_to_domain(group_json: Dict[str, Any]) -> StockGroup:
        g_name = group_json.get("name", "")
        return StockGroup(
            name=g_name,
            series_code=group_json.get("series_code") or (g_name.split()[0] if g_name else "GEN")
        )

    @staticmethod
    def to_purchase_order_list(items_json: List[Dict[str, Any]]) -> List[PurchaseOrder]:
        pos = []
        for raw in items_json:
            purc_due = float(raw.get("purchase_pending", 0.0))
            if purc_due > 0:
                pos.append(PurchaseOrder(
                    part_number=raw.get("part_number") or raw.get("name", ""),
                    make=Config.DEFAULT_MAKE,
                    purc_orders_pending=purc_due,
                    current_stock=float(raw.get("closing_balance", 0.0)),
                    nett_available=float(raw.get("nett_available", 0.0))
                ))
        return pos

    @staticmethod
    def to_sales_order_list(items_json: List[Dict[str, Any]]) -> List[SalesOrder]:
        sos = []
        for raw in items_json:
            sale_due = float(raw.get("sales_due", 0.0))
            if sale_due > 0:
                sos.append(SalesOrder(
                    part_number=raw.get("part_number") or raw.get("name", ""),
                    make=Config.DEFAULT_MAKE,
                    sale_orders_due=sale_due,
                    current_stock=float(raw.get("closing_balance", 0.0)),
                    nett_available=float(raw.get("nett_available", 0.0))
                ))
        return sos

    @staticmethod
    def to_inventory_dict_list(items_json: List[Dict[str, Any]], search_query: Optional[str] = None, only_reorder: bool = False) -> List[dict]:
        inventory = []
        for raw in items_json:
            p_num = raw.get("part_number") or raw.get("name", "")
            if search_query and search_query.lower() not in p_num.lower():
                continue

            shortfall = float(raw.get("shortfall", 0.0))
            if only_reorder and shortfall <= 0:
                continue

            reorder_lvl = float(raw.get("reorder_level", 0.0))
            inventory.append({
                "Part Number": p_num,
                "Make": Config.DEFAULT_MAKE,
                "Closing Stock": float(raw.get("closing_balance", 0.0)),
                "Purc Orders Pending": float(raw.get("purchase_pending", 0.0)),
                "Sale Orders Due": float(raw.get("sales_due", 0.0)),
                "Nett Available": float(raw.get("nett_available", 0.0)),
                "Min Reorder Qty": reorder_lvl,
                "Reorder Level": reorder_lvl,
                "Short Fall": shortfall,
                "Order To Be Placed": shortfall,
                "Last Updated": raw.get("updated_at", "")[:10] or "2026-01-01"
            })
        return inventory
