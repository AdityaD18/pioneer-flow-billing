import sqlite3
from datetime import datetime
from app.models.database import query_db, execute_db

class CustomerService:
    @staticmethod
    def get_customers(search_query=None):
        """Retrieves customers, optionally filtered by search text."""
        if search_query:
            q = f"%{search_query}%"
            rows = query_db(
                "SELECT * FROM CUSTOMERS WHERE name LIKE ? OR gst_number LIKE ? ORDER BY name ASC",
                (q, q)
            )
        else:
            rows = query_db("SELECT * FROM CUSTOMERS ORDER BY name ASC")
        
        return [dict(r) for r in rows]

    @staticmethod
    def get_customer_by_id(customer_id):
        """Retrieves a single customer by their database ID."""
        row = query_db("SELECT * FROM CUSTOMERS WHERE id = ?", (customer_id,), one=True)
        return dict(row) if row else None

    @staticmethod
    def get_customer_by_name(name):
        """Retrieves a single customer by their exact name."""
        row = query_db("SELECT * FROM CUSTOMERS WHERE name = ?", (name.strip(),), one=True)
        return dict(row) if row else None

    @staticmethod
    def create_customer(name, discount_percentage, gst_number=None, payment_terms=None):
        """Creates a new customer record."""
        name_clean = name.strip()
        if not name_clean:
            raise ValueError("Customer name cannot be empty.")
        
        # Check if already exists
        existing = CustomerService.get_customer_by_name(name_clean)
        if existing:
            raise ValueError(f"Customer with name '{name_clean}' already exists.")
        
        try:
            discount = float(discount_percentage)
        except (ValueError, TypeError):
            discount = 0.0
            
        now_str = datetime.now().isoformat()
        customer_id = execute_db(
            """INSERT INTO CUSTOMERS (name, discount_percentage, gst_number, payment_terms, created_at, updated_at) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name_clean, discount, gst_number or None, payment_terms or None, now_str, now_str)
        )
        return CustomerService.get_customer_by_id(customer_id)

    @staticmethod
    def update_customer(customer_id, name, discount_percentage, gst_number=None, payment_terms=None):
        """Updates an existing customer record."""
        customer = CustomerService.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError("Customer not found.")
        
        name_clean = name.strip()
        if not name_clean:
            raise ValueError("Customer name cannot be empty.")
            
        # Check duplicate name on other records
        existing = CustomerService.get_customer_by_name(name_clean)
        if existing and existing['id'] != int(customer_id):
            raise ValueError(f"Another customer with name '{name_clean}' already exists.")
            
        try:
            discount = float(discount_percentage)
        except (ValueError, TypeError):
            discount = 0.0
            
        now_str = datetime.now().isoformat()
        execute_db(
            """UPDATE CUSTOMERS 
               SET name = ?, discount_percentage = ?, gst_number = ?, payment_terms = ?, updated_at = ? 
               WHERE id = ?""",
            (name_clean, discount, gst_number or None, payment_terms or None, now_str, customer_id)
        )
        return CustomerService.get_customer_by_id(customer_id)

    @staticmethod
    def delete_customer(customer_id):
        """Deletes a customer record from the database."""
        customer = CustomerService.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError("Customer not found.")
        
        # Check if they have invoices/orders
        orders = query_db("SELECT id FROM ORDERS WHERE customer_id = ? LIMIT 1", (customer_id,))
        if orders:
            raise ValueError("Cannot delete customer because they have order history associated with them.")
            
        execute_db("DELETE FROM CUSTOMERS WHERE id = ?", (customer_id,))
        return True
