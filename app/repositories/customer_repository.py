from datetime import datetime
from app.repositories.base_repository import BaseRepository

class CustomerRepository(BaseRepository):
    """Centralized repository for CUSTOMERS table access."""

    @classmethod
    def get_all(cls, search_query=None):
        if search_query:
            q = f"%{search_query}%"
            rows = cls.query(
                "SELECT * FROM CUSTOMERS WHERE name LIKE ? OR gst_number LIKE ? ORDER BY name ASC",
                (q, q)
            )
        else:
            rows = cls.query("SELECT * FROM CUSTOMERS ORDER BY name ASC")
        return [dict(r) for r in rows]

    @classmethod
    def get_by_id(cls, customer_id):
        row = cls.query("SELECT * FROM CUSTOMERS WHERE id = ?", (customer_id,), one=True)
        return dict(row) if row else None

    @classmethod
    def get_by_name(cls, name):
        row = cls.query("SELECT * FROM CUSTOMERS WHERE name = ?", (name.strip(),), one=True)
        return dict(row) if row else None

    @classmethod
    def save(cls, name, discount_percentage, gst_number=None, payment_terms=None):
        now_str = datetime.now().isoformat()
        return cls.execute(
            """INSERT INTO CUSTOMERS (name, discount_percentage, gst_number, payment_terms, created_at, updated_at) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name.strip(), discount_percentage, gst_number or None, payment_terms or None, now_str, now_str)
        )

    @classmethod
    def update(cls, customer_id, name, discount_percentage, gst_number=None, payment_terms=None):
        now_str = datetime.now().isoformat()
        cls.execute(
            """UPDATE CUSTOMERS 
               SET name = ?, discount_percentage = ?, gst_number = ?, payment_terms = ?, updated_at = ? 
               WHERE id = ?""",
            (name.strip(), discount_percentage, gst_number or None, payment_terms or None, now_str, customer_id)
        )

    @classmethod
    def delete(cls, customer_id):
        cls.execute("DELETE FROM CUSTOMERS WHERE id = ?", (customer_id,))

    @classmethod
    def has_orders(cls, customer_id):
        row = cls.query("SELECT id FROM ORDERS WHERE customer_id = ? LIMIT 1", (customer_id,), one=True)
        return row is not None
