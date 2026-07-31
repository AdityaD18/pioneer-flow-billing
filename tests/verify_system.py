import os
import sys
import unittest
import sqlite3
import threading
from datetime import datetime

# Add the parent directory of app to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, g
from app.models.database import init_db, get_db_connection, DATABASE_PATH
from app.services.import_service import ImportService
from app.services.customer_service import CustomerService
from app.services.order_service import OrderService
from app.services.invoice_service import InvoiceService

class TestInvoiceSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure database is clean and initialized
        if os.path.exists(DATABASE_PATH):
            try:
                os.remove(DATABASE_PATH)
            except PermissionError:
                pass
        init_db()
        cls.app = Flask(__name__)

    def setUp(self):
        # Setup application context for each test
        self.ctx = self.app.app_context()
        self.ctx.push()
        g._database = get_db_connection()

    def tearDown(self):
        # Close connection and tear down context
        if hasattr(g, '_database'):
            g._database.close()
        self.ctx.pop()

    def test_a_excel_imports(self):
        print("\n=== Testing Excel Imports ===")
        excel_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'group order status.xlsx'))
        
        # Test Inventory Import
        print(f"Importing inventory from {excel_path}...")
        inv_result = ImportService.import_inventory(excel_path)
        print(f"Inventory Import Result: {inv_result['status']} | Processed: {inv_result['total_records']} | Success: {inv_result['successful_records']} | Fail: {inv_result['failed_records']}")
        self.assertIn(inv_result['status'], ['success', 'partial_success'])
        self.assertGreater(inv_result['successful_records'], 0)
        
        # Test Cost Import
        print(f"Importing costs from {excel_path}...")
        cost_result = ImportService.import_costs(excel_path)
        print(f"Cost Import Result: {cost_result['status']} | Processed: {cost_result['total_records']} | Success: {cost_result['successful_records']} | Fail: {cost_result['failed_records']}")
        self.assertIn(cost_result['status'], ['success', 'partial_success'])
        self.assertGreater(cost_result['successful_records'], 0)

        # Check in DB
        prod_count = query_db("SELECT COUNT(*) as c FROM PRODUCTS", one=True)['c']
        inv_count = query_db("SELECT COUNT(*) as c FROM INVENTORY", one=True)['c']
        cost_count = query_db("SELECT COUNT(*) as c FROM PRODUCT_COSTS WHERE is_current=1", one=True)['c']
        import_logs = query_db("SELECT COUNT(*) as c FROM IMPORT_LOG", one=True)['c']
        
        print(f"Database Stats - Products: {prod_count}, Inventory Stocks: {inv_count}, Active Costs: {cost_count}, Logs: {import_logs}")
        self.assertGreater(prod_count, 0)
        self.assertGreater(inv_count, 0)
        self.assertGreater(cost_count, 0)
        self.assertEqual(import_logs, 2)

    def test_b_customer_management(self):
        print("\n=== Testing Customer Management ===")
        # 1. Create Customer
        cust = CustomerService.create_customer("Pioneer Automation Corp", 12.5, "27AAAAA1234A1Z1", "Net 30 Days")
        self.assertEqual(cust['name'], "Pioneer Automation Corp")
        self.assertEqual(cust['discount_percentage'], 12.5)
        self.assertEqual(cust['gst_number'], "27AAAAA1234A1Z1")
        self.assertEqual(cust['payment_terms'], "Net 30 Days")
        print(f"Created Customer: {cust['name']} (ID: {cust['id']})")
        
        # 2. Update Customer
        updated = CustomerService.update_customer(cust['id'], "Pioneer Automation Corp Updated", 15.0, "27AAAAA1234A1Z2", "Net 15 Days")
        self.assertEqual(updated['name'], "Pioneer Automation Corp Updated")
        self.assertEqual(updated['discount_percentage'], 15.0)
        self.assertEqual(updated['payment_terms'], "Net 15 Days")
        print(f"Updated Customer: {updated['name']} (Discount: {updated['discount_percentage']}%)")
        
        # 3. Retrieve
        retrieved = CustomerService.get_customer_by_id(cust['id'])
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['name'], "Pioneer Automation Corp Updated")
        
    def test_c_invoice_flow_and_calculation(self):
        print("\n=== Testing Invoice Flow & Pricing Calculations ===")
        
        # Fetch some active product
        product = query_db(
            """SELECT p.id, p.part_number, i.current_stock, c.price_per_100_pcs 
               FROM PRODUCTS p
               JOIN INVENTORY i ON p.id = i.product_id
               JOIN PRODUCT_COSTS c ON p.id = c.product_id AND c.is_current = 1
               WHERE i.current_stock > 10
               LIMIT 1""", one=True
        )
        
        self.assertIsNotNone(product, "No products with stock found to run invoice test.")
        print(f"Selected Test Product: {product['part_number']} | Stock: {product['current_stock']} | Cost per 100pcs: INR {product['price_per_100_pcs']}")
        
        # 1. Test pricing calculation preview
        customer_data = {
            "name": "Quicktest Client",
            "discount_percentage": 10.0,
            "gst_number": "27BBBBB5678B2Z2",
            "payment_terms": "COD"
        }
        
        items_data = [
            {
                "product_id": product['id'],
                "quantity": 50, # 50 pcs
                "discount_percentage": None # Fallback to customer's 10%
            }
        ]
        
        calc = OrderService.calculate_order(customer_data, items_data)
        print(f"Calculated Subtotal: INR {calc['subtotal']} | GST Amount: INR {calc['gst_amount']} | Grand Total: INR {calc['grand_total']}")
        
        # Check calculation: line_total = (50 * price_per_100 * (1 - 0.1)) / 100 = 0.5 * price * 0.9 = 0.45 * price_per_100
        expected_subtotal = round((50 * float(product['price_per_100_pcs']) * (1 - 0.1)) / 100.0, 2)
        self.assertEqual(calc['subtotal'], expected_subtotal)
        
        # 2. Generate persistent invoice (will trigger inline customer save)
        invoice_payload = {
            "customer": customer_data,
            "items": items_data,
            "invoice_date": "2026-07-31"
        }
        
        order_id = OrderService.create_order(invoice_payload['customer'], invoice_payload['items'])
        invoice_id = InvoiceService.generate_invoice_for_order(order_id, invoice_payload['invoice_date'])
        
        invoice = InvoiceService.get_invoice_by_id(invoice_id)
        print(f"Generated Invoice Number: {invoice['invoice_number']} | Date: {invoice['invoice_date']}")
        
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice['invoice_number'][:4], "INV-")
        self.assertEqual(invoice['order']['customer_name_snapshot'], "Quicktest Client")
        self.assertEqual(invoice['items'][0]['part_number_snapshot'], product['part_number'])
        self.assertEqual(invoice['items'][0]['quantity'], 50)
        
        # Assert stock is NOT reduced
        post_stock = query_db("SELECT current_stock FROM INVENTORY WHERE product_id = ?", (product['id'],), one=True)['current_stock']
        self.assertEqual(post_stock, product['current_stock'], "Inventory should not change during invoice creation in MVP.")
        print(f"Confirmed Stock Verification: Level remained unchanged at {post_stock}")

    def test_d_concurrent_invoice_number_safety(self):
        print("\n=== Testing Concurrent Invoice Number Generation Thread Safety ===")
        
        invoice_numbers = []
        threads = []
        errors = []
        
        # We will spin 10 threads to generate invoices concurrently
        def generate_worker(thread_idx, flask_app):
            # Create a separate application context for each thread
            with flask_app.app_context():
                try:
                    # Thread gets its own connection
                    g._database = get_db_connection()
                    
                    # Create unique customer for each order
                    cust_name = f"Concurrent Customer {thread_idx}"
                    customer = CustomerService.create_customer(cust_name, 5.0)
                    
                    # Fetch first product
                    prod = query_db("SELECT id FROM PRODUCTS LIMIT 1", one=True)
                    items = [{"product_id": prod['id'], "quantity": 10}]
                    
                    order_id = OrderService.create_order(customer, items)
                    invoice_id = InvoiceService.generate_invoice_for_order(order_id)
                    invoice = InvoiceService.get_invoice_by_id(invoice_id)
                    
                    invoice_numbers.append(invoice['invoice_number'])
                    g._database.close()
                except Exception as ex:
                    errors.append(str(ex))
        
        # Run 10 threads in parallel
        for idx in range(10):
            t = threading.Thread(target=generate_worker, args=(idx, self.app))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        print(f"Generated concurrently: {len(invoice_numbers)} invoices.")
        print(f"Invoices list: {invoice_numbers}")
        if errors:
            print(f"Thread errors logged: {errors}")
            
        self.assertEqual(len(errors), 0, f"Errors occurred during concurrent execution: {errors}")
        self.assertEqual(len(invoice_numbers), 10)
        self.assertEqual(len(set(invoice_numbers)), 10, "Duplicate invoice numbers detected under concurrent threads!")
        print("Success: Checked unique sequence numbers for parallel creations.")

# Helper queries
def query_db(query, args=(), one=False):
    cur = g._database.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

if __name__ == '__main__':
    unittest.main()
