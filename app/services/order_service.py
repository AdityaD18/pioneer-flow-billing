from app.models.database import query_db, execute_db, get_db
from app.services.customer_service import CustomerService
from datetime import datetime

class OrderService:
    @staticmethod
    def get_settings():
        """Reads application settings."""
        rows = query_db("SELECT key, value FROM APP_SETTINGS")
        return {r['key']: r['value'] for r in rows}

    @staticmethod
    def get_gst_rate():
        """Helper to get default GST rate from settings."""
        settings = OrderService.get_settings()
        try:
            return float(settings.get('gst_rate', 18.0))
        except ValueError:
            return 18.0

    @classmethod
    def calculate_order(cls, customer_data, items_data):
        """
        Calculates pricing, line totals, subtotal, GST, and grand total.
        items_data format: list of dicts: {'product_id': X, 'quantity': Y, 'discount_percentage': Z}
        customer_data format: dict: {'id': X, 'name': 'Name', 'discount_percentage': D, ...}
        
        Returns:
            dict containing calculated order structure + stock warnings
        """
        gst_rate = cls.get_gst_rate()
        subtotal = 0.0
        calculated_items = []
        has_warnings = False
        
        # Load customer default discount if not provided in item
        cust_discount = float(customer_data.get('discount_percentage', 0) or 0)
        
        for item in items_data:
            product_id = item.get('product_id')
            qty = float(item.get('quantity', 0) or 0)
            
            # Fetch product details with active price and stock
            prod = query_db(
                """SELECT p.*, i.current_stock, c.price_per_100_pcs, c.price_per_unit 
                   FROM PRODUCTS p
                   LEFT JOIN INVENTORY i ON p.id = i.product_id
                   LEFT JOIN PRODUCT_COSTS c ON p.id = c.product_id AND c.is_current = 1
                   WHERE p.id = ?""",
                (product_id,), one=True
            )
            
            if not prod:
                raise ValueError(f"Product ID {product_id} not found in database.")
            
            # Determine unit price per piece (rate per pc)
            if item.get('unit_price') is not None:
                price_per_unit = float(item['unit_price'])
            elif item.get('unit_price_100') is not None:
                price_per_unit = float(item['unit_price_100']) / 100.0
            elif prod['price_per_unit'] is not None:
                price_per_unit = float(prod['price_per_unit'])
            else:
                price_per_unit = float(prod['price_per_100_pcs'] or 0) / 100.0

            current_stock = float(prod['current_stock'] or 0)
            
            # Use item discount percentage or fallback to customer default
            discount_pct = item.get('discount_percentage')
            if discount_pct is None or discount_pct == '':
                discount_pct = cust_discount
            else:
                discount_pct = float(discount_pct)
                
            # Line total: Qty * Price_per_piece * (1 - disc%)
            discounted_unit_price = price_per_unit * (1 - (discount_pct / 100.0))
            line_total = qty * discounted_unit_price
            subtotal += line_total
            
            # Check stock warning (Verification only, no auto subtraction)
            insufficient_stock = qty > current_stock
            if insufficient_stock:
                has_warnings = True
                
            calculated_items.append({
                "product_id": prod["id"],
                "part_number": prod["part_number"],
                "part_name": prod["part_name"] or prod["part_number"],
                "quantity": qty,
                "current_stock": current_stock,
                "unit_price": price_per_unit,
                "unit_price_100": price_per_unit * 100.0,
                "discount_percentage": discount_pct,
                "gst_percentage": gst_rate,
                "line_total": round(line_total, 2),
                "insufficient_stock": insufficient_stock
            })
            
        gst_amount = subtotal * (gst_rate / 100.0)
        grand_total = subtotal + gst_amount
        
        return {
            "customer": {
                "name": customer_data.get('name'),
                "gst_number": customer_data.get('gst_number'),
                "payment_terms": customer_data.get('payment_terms'),
                "discount_percentage": cust_discount
            },
            "items": calculated_items,
            "subtotal": round(subtotal, 2),
            "gst_rate": gst_rate,
            "gst_amount": round(gst_amount, 2),
            "grand_total": round(grand_total, 2),
            "has_warnings": has_warnings
        }

    @classmethod
    def create_order(cls, customer_input, items_input):
        """
        Calculates and creates a persistent Order.
        Saves inline customers if they do not exist.
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
            
        # Check if customer exists in DB or create inline
        cust = None
        if customer_id:
            cust = CustomerService.get_customer_by_id(customer_id)
        else:
            # Match by exact name
            cust = CustomerService.get_customer_by_name(customer_name)
            
        if not cust:
            # Inline creation!
            cust = CustomerService.create_customer(
                name=customer_name,
                discount_percentage=discount_percentage,
                gst_number=gst_number,
                payment_terms=payment_terms
            )
            customer_id = cust['id']
        else:
            customer_id = cust['id']
            # Optionally update fields if user provided different inline values?
            # Normally we just snapshot the provided inline details for this order.
        
        # 2. Perform Calculations
        calc = cls.calculate_order(cust, items_input)
        
        # 3. Save Order (wrap in transaction)
        try:
            cur.execute("BEGIN IMMEDIATE TRANSACTION;")
            
            # Generate a temporary unique order number
            temp_order_num = f"ORD-TEMP-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            
            cur.execute(
                """INSERT INTO ORDERS (
                        order_number, customer_id, customer_name_snapshot, 
                        customer_gst_snapshot, customer_terms_snapshot, 
                        discount_percentage, subtotal, discount_amount, 
                        gst_amount, grand_total, gst_rate
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    temp_order_num, customer_id, customer_name,
                    gst_number or cust['gst_number'], payment_terms or cust['payment_terms'],
                    discount_percentage, calc['subtotal'], 0.0, # discount is applied per-item
                    calc['gst_amount'], calc['grand_total'], calc['gst_rate']
                )
            )
            order_id = cur.lastrowid
            
            # Update order number with auto-increment ID to prevent duplicate collisions
            order_number = f"ORD-{datetime.now().year}-{order_id:05d}"
            cur.execute("UPDATE ORDERS SET order_number = ? WHERE id = ?", (order_number, order_id))
            
            # Save items
            for item in calc['items']:
                cur.execute(
                    """INSERT INTO ORDER_ITEMS (
                            order_id, product_id, part_number_snapshot, part_name_snapshot, 
                            quantity, unit_price, discount_percentage, gst_percentage, line_total
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        order_id, item['product_id'], item['part_number'], item['part_name'],
                        item['quantity'], item['unit_price_100'], item['discount_percentage'],
                        item['gst_percentage'], item['line_total']
                    )
                )
                
            conn.commit()
            return order_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cur.close()
            
    @classmethod
    def get_order_by_id(cls, order_id):
        """Retrieves order with associated items."""
        order = query_db("SELECT * FROM ORDERS WHERE id = ?", (order_id,), one=True)
        if not order:
            return None
            
        items = query_db("SELECT * FROM ORDER_ITEMS WHERE order_id = ?", (order_id,))
        
        result = dict(order)
        result['items'] = [dict(i) for i in items]
        return result
