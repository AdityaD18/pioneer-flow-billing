from app.repositories.base_repository import BaseRepository

class QuotationRepository(BaseRepository):
    """Centralized repository for QUOTATIONS and QUOTATION_SEQUENCE tables access."""

    @classmethod
    def get_all(cls, search_query=None):
        if search_query:
            q = f"%{search_query}%"
            rows = cls.query(
                """SELECT q.* 
                   FROM QUOTATIONS q
                   WHERE q.quotation_number LIKE ? OR q.customer_name_snapshot LIKE ?
                   ORDER BY q.created_at DESC""",
                (q, q)
            )
        else:
            rows = cls.query(
                """SELECT q.* 
                   FROM QUOTATIONS q
                   ORDER BY q.created_at DESC"""
            )
        return [dict(r) for r in rows]

    @classmethod
    def get_by_id(cls, quotation_id):
        q = cls.query("SELECT * FROM QUOTATIONS WHERE id = ?", (quotation_id,), one=True)
        if not q:
            return None
            
        items = cls.query("SELECT * FROM QUOTATION_ITEMS WHERE quotation_id = ?", (quotation_id,))
        
        result = dict(q)
        result['order'] = {
            "order_number": q['quotation_number'],
            "customer_name_snapshot": q['customer_name_snapshot'],
            "customer_gst_snapshot": q['customer_gst_snapshot'],
            "customer_terms_snapshot": q['customer_terms_snapshot'],
            "discount_percentage": q['discount_percentage'],
            "subtotal": q['subtotal'],
            "gst_amount": q['gst_amount'],
            "gst_rate": q['gst_rate'],
            "grand_total": q['grand_total']
        }
        result['items'] = [dict(item) for item in items]
        return result
