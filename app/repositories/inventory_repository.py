from datetime import datetime
from app.repositories.base_repository import BaseRepository

class InventoryRepository(BaseRepository):
    """Centralized repository for INVENTORY table access."""

    @classmethod
    def get_by_product_id(cls, product_id):
        row = cls.query("SELECT * FROM INVENTORY WHERE product_id = ?", (product_id,), one=True)
        return dict(row) if row else None

    @classmethod
    def update_stock(cls, product_id, current_stock):
        row = cls.get_by_product_id(product_id)
        if row is None:
            cls.execute(
                "INSERT INTO INVENTORY (product_id, current_stock, last_updated) VALUES (?, ?, datetime('now'))",
                (product_id, current_stock)
            )
        else:
            cls.execute(
                "UPDATE INVENTORY SET current_stock = ?, last_updated = datetime('now') WHERE product_id = ?",
                (current_stock, product_id)
            )

    @classmethod
    def get_stock_sheet(cls, search_kw=None, only_reorder=False):
        sql = """
            SELECT 
                p.part_number as "Part Number",
                p.make as "Make",
                COALESCE(i.current_stock, 0.0) as "Closing Stock",
                COALESCE(i.purc_orders_pending, 0.0) as "Purc Orders Pending",
                COALESCE(i.sale_orders_due, 0.0) as "Sale Orders Due",
                COALESCE(i.nett_available, 0.0) as "Nett Available",
                COALESCE(i.reorder_level, 0.0) as "Reorder Level",
                COALESCE(i.short_fall, 0.0) as "Short Fall",
                COALESCE(i.min_reorder_qty, 0.0) as "Min Reorder Qty",
                COALESCE(i.order_to_be_placed, 0.0) as "Order To Be Placed",
                i.last_updated as "Last Updated"
            FROM INVENTORY i
            JOIN PRODUCTS p ON i.product_id = p.id
            WHERE 1=1
        """
        params = []
        if search_kw:
            sql += " AND p.part_number LIKE ?"
            params.append(f"%{search_kw}%")
        if only_reorder:
            sql += " AND (i.short_fall > 0 OR i.order_to_be_placed > 0)"
            
        sql += " ORDER BY p.part_number ASC LIMIT 10000"
        rows = cls.query(sql, params)
        return [dict(r) for r in rows]
