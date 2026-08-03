from abc import ABC, abstractmethod

class BaseDataProvider(ABC):
    """Abstract Data Provider interface establishing source-agnostic data contracts for Pioneer Flow Billing."""

    @abstractmethod
    def get_stock_items(self, search_kw=None, series=None):
        """Retrieves catalog product items."""
        pass

    @abstractmethod
    def get_stock_groups(self):
        """Retrieves distinct stock groups or product series."""
        pass

    @abstractmethod
    def get_customers(self, search_query=None):
        """Retrieves customer accounts."""
        pass

    @abstractmethod
    def get_ledgers(self):
        """Retrieves ledger accounts."""
        pass

    @abstractmethod
    def get_orders(self):
        """Retrieves orders."""
        pass

    @abstractmethod
    def get_purchase_orders(self):
        """Retrieves purchase orders."""
        pass

    @abstractmethod
    def get_sales_orders(self):
        """Retrieves sales orders."""
        pass

    @abstractmethod
    def get_inventory(self, search_query=None, only_reorder=False):
        """Retrieves inventory stock reorder status records."""
        pass

    @abstractmethod
    def get_company_details(self):
        """Retrieves company metadata details."""
        pass

    @abstractmethod
    def save_invoice(self, order_id, invoice_date=None):
        """Generates and persists an invoice for an order."""
        pass

    @abstractmethod
    def update_inventory(self, product_id, new_stock_qty):
        """Updates stock quantity for a product."""
        pass

    @abstractmethod
    def search_item(self, query):
        """Searches product items by code, name, or make."""
        pass

    @abstractmethod
    def import_inventory(self, file_path, sheet_name=None, filename='uploaded_file.xlsx', imported_by=None):
        """Imports inventory stock sheet data."""
        pass

    @abstractmethod
    def import_costs(self, file_path, sheet_name=None, filename='uploaded_file.xlsx', imported_by=None):
        """Imports product cost price sheet data."""
        pass

    @abstractmethod
    def sync_from_web_url(self, url, imported_by='Auto Sync'):
        """Syncs inventory stock data from a remote spreadsheet URL."""
        pass
