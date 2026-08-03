from datetime import datetime
from app.repositories.base_repository import BaseRepository

class ProductRepository(BaseRepository):
    """Centralized repository for PRODUCTS and PRODUCT_COSTS tables access."""

    @classmethod
    def get_distinct_series(cls):
        rows = cls.query("SELECT DISTINCT series FROM PRODUCTS WHERE series IS NOT NULL ORDER BY series")
        return [r['series'] for r in rows if r['series']]

    @classmethod
    def get_catalog(cls, search_kw=None, series=None):
        sql = """
            SELECT 
                p.id as product_id,
                p.part_number as "Part Number",
                p.series as "Series",
                p.make as "Make",
                p.packing_quantity as "Packing Qty",
                COALESCE(i.current_stock, 0.0) as "Current Stock (PCS)",
                COALESCE(c.price_per_100_pcs, 0.0) as "Cost / 100 Pcs (INR)",
                COALESCE(c.price_per_unit, 0.0) as "Rate / Pc (INR)"
            FROM PRODUCTS p
            LEFT JOIN INVENTORY i ON p.id = i.product_id
            LEFT JOIN PRODUCT_COSTS c ON p.id = c.product_id AND c.is_current = 1
            WHERE 1=1
        """
        params = []
        if search_kw:
            sql += " AND (p.part_number LIKE ? OR p.make LIKE ?)"
            params.extend([f"%{search_kw}%", f"%{search_kw}%"])
        if series and series != "All Series":
            sql += " AND p.series = ?"
            params.append(series)
            
        sql += " ORDER BY p.part_number ASC LIMIT 10000"
        rows = cls.query(sql, params)
        return [dict(r) for r in rows]

    @classmethod
    def get_all_billing_products(cls):
        sql = """
            SELECT p.id, p.part_number, p.part_name, COALESCE(c.price_per_100_pcs, 0.0) as price_100
            FROM PRODUCTS p
            LEFT JOIN PRODUCT_COSTS c ON p.id = c.product_id AND c.is_current = 1
            ORDER BY p.part_number ASC
        """
        rows = cls.query(sql)
        return [dict(r) for r in rows]

    @classmethod
    def get_by_id(cls, product_id):
        sql = """
            SELECT p.*, i.current_stock, c.price_per_100_pcs, c.price_per_unit 
            FROM PRODUCTS p
            LEFT JOIN INVENTORY i ON p.id = i.product_id
            LEFT JOIN PRODUCT_COSTS c ON p.id = c.product_id AND c.is_current = 1
            WHERE p.id = ?
        """
        row = cls.query(sql, (product_id,), one=True)
        return dict(row) if row else None

    @classmethod
    def get_by_part_number(cls, part_number):
        row = cls.query("SELECT id, packing_quantity FROM PRODUCTS WHERE part_number = ?", (part_number,), one=True)
        return dict(row) if row else None

    @classmethod
    def save_product(cls, part_number, part_name=None, series=None, make="WAGO", packing_quantity=1):
        return cls.execute(
            "INSERT INTO PRODUCTS (part_number, part_name, series, make, packing_quantity) VALUES (?, ?, ?, ?, ?)",
            (part_number, part_name or part_number, series, make, packing_quantity)
        )

    @classmethod
    def update_packing_and_series(cls, product_id, packing_quantity, series):
        cls.execute(
            "UPDATE PRODUCTS SET packing_quantity = ?, series = ? WHERE id = ?",
            (packing_quantity, series, product_id)
        )

    @classmethod
    def update_cost_price(cls, product_id, price_per_100_pcs):
        new_punit = price_per_100_pcs / 100.0
        cls.execute("UPDATE PRODUCT_COSTS SET is_current = 0 WHERE product_id = ? AND is_current = 1", (product_id,))
        cls.execute(
            "INSERT INTO PRODUCT_COSTS (product_id, price_per_100_pcs, price_per_unit, effective_from, is_current) VALUES (?, ?, ?, datetime('now'), 1)",
            (product_id, price_per_100_pcs, new_punit)
        )
