from app.repositories.base_repository import BaseRepository

class InvoiceRepository(BaseRepository):
    """Centralized repository for INVOICES and INVOICE_SEQUENCE tables access."""

    @classmethod
    def get_all(cls, search_query=None):
        if search_query:
            q = f"%{search_query}%"
            rows = cls.query(
                """SELECT i.*, o.customer_name_snapshot, o.grand_total, o.order_number 
                   FROM INVOICES i
                   JOIN ORDERS o ON i.order_id = o.id
                   WHERE i.invoice_number LIKE ? OR o.customer_name_snapshot LIKE ?
                   ORDER BY i.created_at DESC""",
                (q, q)
            )
        else:
            rows = cls.query(
                """SELECT i.*, o.customer_name_snapshot, o.grand_total, o.order_number 
                   FROM INVOICES i
                   JOIN ORDERS o ON i.order_id = o.id
                   ORDER BY i.created_at DESC"""
            )
        return [dict(r) for r in rows]

    @classmethod
    def get_by_id(cls, invoice_id):
        inv = cls.query("SELECT * FROM INVOICES WHERE id = ?", (invoice_id,), one=True)
        if not inv:
            return None
            
        order_id = inv['order_id']
        order_details = cls.query("SELECT * FROM ORDERS WHERE id = ?", (order_id,), one=True)
        if not order_details:
            return None
            
        items = cls.query("SELECT * FROM ORDER_ITEMS WHERE order_id = ?", (order_id,))
        
        result = dict(inv)
        result['order'] = dict(order_details)
        result['items'] = [dict(item) for item in items]
        return result

    @classmethod
    def get_by_order_id(cls, order_id):
        row = cls.query("SELECT id, invoice_number FROM INVOICES WHERE order_id = ?", (order_id,), one=True)
        return dict(row) if row else None
