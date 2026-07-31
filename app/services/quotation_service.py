import sqlite3
from datetime import datetime
from app.models.database import get_db, query_db, get_db_connection
from app.services.customer_service import CustomerService
from app.services.order_service import OrderService

class QuotationService:
    @classmethod
    def generate_quotation(cls, customer_input, items_input, quotation_date=None):
        """
        Creates and persists a Quotation with a unique sequential QTN number.
        Uses SQLite IMMEDIATE transaction sequencing to prevent duplicates.
        """
        conn = get_db()
        cur = conn.cursor()
        
        # 1. Resolve customer
        customer_id = customer_input.get('id')
        customer_name = str(customer_input.get('name', '')).strip()
        discount_percentage = float(customer_input.get('discount_percentage', 0) or 0)
        gst_number = customer_input.get('gst_number')
        payment_terms = customer_input.get('payment_terms')
        
        if not customer_name:
            raise ValueError("Customer name is required.")
            
        cust = None
        if customer_id:
            cust = CustomerService.get_customer_by_id(customer_id)
        else:
            cust = CustomerService.get_customer_by_name(customer_name)
            
        if not cust:
            cust = CustomerService.create_customer(
                name=customer_name,
                discount_percentage=discount_percentage,
                gst_number=gst_number,
                payment_terms=payment_terms
            )
            customer_id = cust['id']
        else:
            customer_id = cust['id']
            
        # 2. Perform calculations
        calc = OrderService.calculate_order(cust, items_input)
        
        if not quotation_date:
            quotation_date = datetime.now().strftime('%Y-%m-%d')
            
        current_year = str(datetime.now().year)
        
        try:
            # Wrap in write lock transaction
            cur.execute("BEGIN IMMEDIATE TRANSACTION;")
            
            # 1. Fetch next sequence number for this year
            cur.execute(
                """SELECT seq_number FROM QUOTATION_SEQUENCE 
                   WHERE year = ? 
                   ORDER BY seq_number DESC LIMIT 1""",
                (current_year,)
            )
            latest = cur.fetchone()
            next_seq = 1001 if latest is None else latest['seq_number'] + 1
            
            # 2. Insert sequence tracking record to claim it
            cur.execute(
                "INSERT INTO QUOTATION_SEQUENCE (year, seq_number) VALUES (?, ?)",
                (current_year, next_seq)
            )
            
            # Format sequence number: QTN-YYYY-XXXXX
            quotation_number = f"QTN-{current_year}-{next_seq:05d}"
            
            # 3. Create quotation
            cur.execute(
                """INSERT INTO QUOTATIONS (
                        quotation_number, customer_id, customer_name_snapshot, 
                        customer_gst_snapshot, customer_terms_snapshot, 
                        discount_percentage, subtotal, discount_amount, 
                        gst_amount, grand_total, gst_rate, created_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    quotation_number, customer_id, customer_name,
                    gst_number or cust['gst_number'], payment_terms or cust['payment_terms'],
                    discount_percentage, calc['subtotal'], 0.0,
                    calc['gst_amount'], calc['grand_total'], calc['gst_rate'],
                    datetime.now().isoformat()
                )
            )
            quotation_id = cur.lastrowid
            
            # Save quotation items
            for item in calc['items']:
                cur.execute(
                    """INSERT INTO QUOTATION_ITEMS (
                            quotation_id, product_id, part_number_snapshot, 
                            part_name_snapshot, quantity, unit_price, 
                            discount_percentage, gst_percentage, line_total
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        quotation_id, item['product_id'], item['part_number'],
                        item['part_name'], item['quantity'], item['unit_price_100'],
                        item['discount_percentage'], item['gst_percentage'], item['line_total']
                    )
                )
                
            conn.commit()
            return quotation_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cur.close()

    @staticmethod
    def get_quotations(search_query=None):
        """Retrieves past quotations, optionally filtering by quotation number or customer name."""
        if search_query:
            q = f"%{search_query}%"
            rows = query_db(
                """SELECT q.* 
                   FROM QUOTATIONS q
                   WHERE q.quotation_number LIKE ? OR q.customer_name_snapshot LIKE ?
                   ORDER BY q.created_at DESC""",
                (q, q)
            )
        else:
            rows = query_db(
                """SELECT q.* 
                   FROM QUOTATIONS q
                   ORDER BY q.created_at DESC"""
            )
        return [dict(r) for r in rows]

    @classmethod
    def get_quotation_by_id(cls, quotation_id):
        """Retrieves complete details for a specific quotation, including items."""
        q = query_db("SELECT * FROM QUOTATIONS WHERE id = ?", (quotation_id,), one=True)
        if not q:
            return None
            
        items = query_db("SELECT * FROM QUOTATION_ITEMS WHERE quotation_id = ?", (quotation_id,))
        
        # Structure payload to match invoice details layout for easy visual reuse
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
