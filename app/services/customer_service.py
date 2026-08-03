from app.repositories.customer_repository import CustomerRepository
from app.core.logger import billing_logger

class CustomerService:
    @staticmethod
    def get_customers(search_query=None):
        """Retrieves customers, optionally filtered by search text."""
        return CustomerRepository.get_all(search_query=search_query)

    @staticmethod
    def get_customer_by_id(customer_id):
        """Retrieves a single customer by their database ID."""
        return CustomerRepository.get_by_id(customer_id)

    @staticmethod
    def get_customer_by_name(name):
        """Retrieves a single customer by their exact name."""
        return CustomerRepository.get_by_name(name)

    @staticmethod
    def create_customer(name, discount_percentage, gst_number=None, payment_terms=None):
        """Creates a new customer record."""
        name_clean = name.strip()
        if not name_clean:
            err_msg = "Customer name cannot be empty."
            billing_logger.warning(f"Customer creation failed: {err_msg}")
            raise ValueError(err_msg)
        
        existing = CustomerRepository.get_by_name(name_clean)
        if existing:
            err_msg = f"Customer with name '{name_clean}' already exists."
            billing_logger.warning(f"Customer creation failed: {err_msg}")
            raise ValueError(err_msg)
        
        try:
            discount = float(discount_percentage)
        except (ValueError, TypeError):
            discount = 0.0
            
        customer_id = CustomerRepository.save(name_clean, discount, gst_number=gst_number, payment_terms=payment_terms)
        billing_logger.info(f"Created customer '{name_clean}' (ID: {customer_id}, Discount: {discount}%).")
        return CustomerRepository.get_by_id(customer_id)

    @staticmethod
    def update_customer(customer_id, name, discount_percentage, gst_number=None, payment_terms=None):
        """Updates an existing customer record."""
        customer = CustomerRepository.get_by_id(customer_id)
        if not customer:
            err_msg = "Customer not found."
            billing_logger.warning(f"Customer update failed (ID {customer_id}): {err_msg}")
            raise ValueError(err_msg)
        
        name_clean = name.strip()
        if not name_clean:
            err_msg = "Customer name cannot be empty."
            billing_logger.warning(f"Customer update failed (ID {customer_id}): {err_msg}")
            raise ValueError(err_msg)
            
        existing = CustomerRepository.get_by_name(name_clean)
        if existing and existing['id'] != int(customer_id):
            err_msg = f"Another customer with name '{name_clean}' already exists."
            billing_logger.warning(f"Customer update failed (ID {customer_id}): {err_msg}")
            raise ValueError(err_msg)
            
        try:
            discount = float(discount_percentage)
        except (ValueError, TypeError):
            discount = 0.0
            
        CustomerRepository.update(customer_id, name_clean, discount, gst_number=gst_number, payment_terms=payment_terms)
        billing_logger.info(f"Updated customer '{name_clean}' (ID: {customer_id}).")
        return CustomerRepository.get_by_id(customer_id)

    @staticmethod
    def delete_customer(customer_id):
        """Deletes a customer record from the database."""
        customer = CustomerRepository.get_by_id(customer_id)
        if not customer:
            err_msg = "Customer not found."
            billing_logger.warning(f"Customer deletion failed (ID {customer_id}): {err_msg}")
            raise ValueError(err_msg)
        
        if CustomerRepository.has_orders(customer_id):
            err_msg = "Cannot delete customer because they have order history associated with them."
            billing_logger.warning(f"Customer deletion blocked for ID {customer_id}: {err_msg}")
            raise ValueError(err_msg)
            
        CustomerRepository.delete(customer_id)
        billing_logger.info(f"Deleted customer '{customer['name']}' (ID: {customer_id}).")
        return True
