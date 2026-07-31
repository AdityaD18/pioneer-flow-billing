import sqlite3
from datetime import datetime
from app.models.database import get_db, query_db, execute_db

class InvoiceService:
    @classmethod
    def generate_invoice_for_order(cls, order_id, invoice_date=None):
        """
        Generates and persists a unique Invoice for a given order_id.
        Uses SQLite IMMEDIATE transaction sequencing to prevent duplicates in concurrent environments.
        """
        conn = get_db()
        cur = conn.cursor()
        
        # Verify order exists
        order = query_db("SELECT id FROM ORDERS WHERE id = ?", (order_id,), one=True)
        if not order:
            raise ValueError(f"Order ID {order_id} not found.")
            
        # Verify invoice doesn't already exist for this order
        existing = query_db("SELECT id, invoice_number FROM INVOICES WHERE order_id = ?", (order_id,), one=True)
        if existing:
            return existing['id']
            
        if not invoice_date:
            invoice_date = datetime.now().strftime('%Y-%m-%d')
            
        current_year = str(datetime.now().year)
        
        try:
            # Wrap in write lock transaction
            cur.execute("BEGIN IMMEDIATE TRANSACTION;")
            
            # 1. Fetch next sequence number for this year
            cur.execute(
                """SELECT seq_number FROM INVOICE_SEQUENCE 
                   WHERE year = ? 
                   ORDER BY seq_number DESC LIMIT 1""",
                (current_year,)
            )
            latest = cur.fetchone()
            next_seq = 1001 if latest is None else latest['seq_number'] + 1
            
            # 2. Insert sequence tracking record to claim it
            cur.execute(
                "INSERT INTO INVOICE_SEQUENCE (year, seq_number) VALUES (?, ?)",
                (current_year, next_seq)
            )
            
            # Format sequence number: INV-YYYY-XXXXX
            invoice_number = f"INV-{current_year}-{next_seq:05d}"
            
            # 3. Create invoice referencing the order
            cur.execute(
                """INSERT INTO INVOICES (invoice_number, order_id, invoice_date, created_at) 
                   VALUES (?, ?, ?, ?)""",
                (invoice_number, order_id, invoice_date, datetime.now().isoformat())
            )
            invoice_id = cur.lastrowid
            
            conn.commit()
            return invoice_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cur.close()

    @staticmethod
    def get_invoices(search_query=None):
        """Retrieves past invoices, optionally filtering by invoice number or customer name."""
        if search_query:
            q = f"%{search_query}%"
            rows = query_db(
                """SELECT i.*, o.customer_name_snapshot, o.grand_total, o.order_number 
                   FROM INVOICES i
                   JOIN ORDERS o ON i.order_id = o.id
                   WHERE i.invoice_number LIKE ? OR o.customer_name_snapshot LIKE ?
                   ORDER BY i.created_at DESC""",
                (q, q)
            )
        else:
            rows = query_db(
                """SELECT i.*, o.customer_name_snapshot, o.grand_total, o.order_number 
                   FROM INVOICES i
                   JOIN ORDERS o ON i.order_id = o.id
                   ORDER BY i.created_at DESC"""
            )
        return [dict(r) for r in rows]

    @classmethod
    def get_invoice_by_id(cls, invoice_id):
        """Retrieves complete details for a specific invoice, including items and order snapshot."""
        inv = query_db("SELECT * FROM INVOICES WHERE id = ?", (invoice_id,), one=True)
        if not inv:
            return None
            
        # Get order details
        order_id = inv['order_id']
        order_details = query_db("SELECT * FROM ORDERS WHERE id = ?", (order_id,), one=True)
        if not order_details:
            return None
            
        items = query_db("SELECT * FROM ORDER_ITEMS WHERE order_id = ?", (order_id,))
        
        result = dict(inv)
        result['order'] = dict(order_details)
        result['items'] = [dict(item) for item in items]
        return result
