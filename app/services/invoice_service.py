from datetime import datetime
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.base_repository import BaseRepository
from app.core.constants import INVOICE_SEQ_PREFIX, DEFAULT_START_SEQ
from app.core.logger import billing_logger

class InvoiceService:
    @classmethod
    def generate_invoice_for_order(cls, order_id, invoice_date=None):
        """
        Generates and persists a unique Invoice for a given order_id.
        Uses SQLite IMMEDIATE transaction sequencing to prevent duplicates in concurrent environments.
        """
        billing_logger.info(f"Generating invoice for order_id: {order_id}")
        
        # Verify order exists
        order = OrderRepository.get_by_id(order_id)
        if not order:
            err_msg = f"Order ID {order_id} not found."
            billing_logger.error(err_msg)
            raise ValueError(err_msg)
            
        # Verify invoice doesn't already exist for this order
        existing = InvoiceRepository.get_by_order_id(order_id)
        if existing:
            billing_logger.info(f"Invoice already exists for order_id {order_id}: {existing['invoice_number']}")
            return existing['id']
            
        if not invoice_date:
            invoice_date = datetime.now().strftime('%Y-%m-%d')
            
        current_year = str(datetime.now().year)
        
        conn = BaseRepository.get_connection()
        cur = conn.cursor()
        
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
            next_seq = DEFAULT_START_SEQ if latest is None else latest['seq_number'] + 1
            
            # 2. Insert sequence tracking record to claim it
            cur.execute(
                "INSERT INTO INVOICE_SEQUENCE (year, seq_number) VALUES (?, ?)",
                (current_year, next_seq)
            )
            
            # Format sequence number: INV-YYYY-XXXXX
            invoice_number = f"{INVOICE_SEQ_PREFIX}-{current_year}-{next_seq:05d}"
            
            # 3. Create invoice referencing the order
            cur.execute(
                """INSERT INTO INVOICES (invoice_number, order_id, invoice_date, created_at) 
                   VALUES (?, ?, ?, ?)""",
                (invoice_number, order_id, invoice_date, datetime.now().isoformat())
            )
            invoice_id = cur.lastrowid
            
            conn.commit()
            billing_logger.info(f"Successfully generated invoice '{invoice_number}' (ID: {invoice_id}) for order_id {order_id}.")
            return invoice_id
        except Exception as e:
            conn.rollback()
            billing_logger.error(f"Failed to generate invoice for order_id {order_id}: {e}", exc_info=True)
            raise e
        finally:
            cur.close()

    @staticmethod
    def get_invoices(search_query=None):
        """Retrieves past invoices, optionally filtering by invoice number or customer name."""
        return InvoiceRepository.get_all(search_query=search_query)

    @classmethod
    def get_invoice_by_id(cls, invoice_id):
        """Retrieves complete details for a specific invoice, including items and order snapshot."""
        return InvoiceRepository.get_by_id(invoice_id)
