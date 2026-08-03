import sqlite3
from datetime import datetime
from app.models.database import query_db, execute_db
from app.core.logger import billing_logger

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
            err_msg = "Customer name cannot be empty."
            billing_logger.warning(f"Customer creation failed: {err_msg}")
            raise ValueError(err_msg)
        
        # Check if already exists
        existing = CustomerService.get_customer_by_name(name_clean)
        if existing:
            err_msg = f"Customer with name '{name_clean}' already exists."
            billing_logger.warning(f"Customer creation failed: {err_msg}")
            raise ValueError(err_msg)
        
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
        billing_logger.info(f"Created customer '{name_clean}' (ID: {customer_id}, Discount: {discount}%).")
        return CustomerService.get_customer_by_id(customer_id)

    @staticmethod
    def update_customer(customer_id, name, discount_percentage, gst_number=None, payment_terms=None):
        """Updates an existing customer record."""
        customer = CustomerService.get_customer_by_id(customer_id)
        if not customer:
            err_msg = "Customer not found."
            billing_logger.warning(f"Customer update failed (ID {customer_id}): {err_msg}")
            raise ValueError(err_msg)
        
        name_clean = name.strip()
        if not name_clean:
            err_msg = "Customer name cannot be empty."
            billing_logger.warning(f"Customer update failed (ID {customer_id}): {err_msg}")
            raise ValueError(err_msg)
            
        existing = CustomerService.get_customer_by_name(name_clean)
        if existing and existing['id'] != int(customer_id):
            err_msg = f"Another customer with name '{name_clean}' already exists."
            billing_logger.warning(f"Customer update failed (ID {customer_id}): {err_msg}")
            raise ValueError(err_msg)
            
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
        billing_logger.info(f"Updated customer '{name_clean}' (ID: {customer_id}).")
        return CustomerService.get_customer_by_id(customer_id)

    @staticmethod
    def delete_customer(customer_id):
        """Deletes a customer record from the database."""
        customer = CustomerService.get_customer_by_id(customer_id)
        if not customer:
            err_msg = "Customer not found."
            billing_logger.warning(f"Customer deletion failed (ID {customer_id}): {err_msg}")
            raise ValueError(err_msg)
        
        orders = query_db("SELECT id FROM ORDERS WHERE customer_id = ? LIMIT 1", (customer_id,))
        if orders:
            err_msg = "Cannot delete customer because they have order history associated with them."
            billing_logger.warning(f"Customer deletion blocked for ID {customer_id}: {err_msg}")
            raise ValueError(err_msg)
            
        execute_db("DELETE FROM CUSTOMERS WHERE id = ?", (customer_id,))
        billing_logger.info(f"Deleted customer '{customer['name']}' (ID: {customer_id}).")
        return True
