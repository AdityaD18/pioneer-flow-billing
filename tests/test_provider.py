import os
import sys
import unittest
from io import BytesIO

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.database import init_db
from app.providers import get_data_provider
from app.models.domain import StockItem, StockGroup, Customer, Ledger, Company, PurchaseOrder, SalesOrder
from app.services.customer_service import CustomerService
from app.services.order_service import OrderService

class TestDataProviderCompliance(unittest.TestCase):
    """
    Automated Provider Contract Compliance Suite.
    Guarantees that any DataProvider implementation (ExcelProvider, TallyProvider, etc.)
    conforms to identical data outputs, type guarantees, and robust error handling.
    """

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.provider = get_data_provider()

    def test_01_company_details(self):
        """Verify provider returns valid Company details domain model."""
        details = self.provider.get_company_details()
        self.assertIsNotNone(details)
        self.assertIsInstance(details, Company)
        self.assertIsInstance(details.company_name, str)
        self.assertGreater(len(details.company_name), 0)

    def test_02_stock_retrieval(self):
        """Verify stock item retrieval returns strongly-typed StockItem instances."""
        items = self.provider.get_stock_items()
        self.assertIsInstance(items, list)
        if items:
            item = items[0]
            self.assertIsInstance(item, StockItem)
            self.assertIsNotNone(item.product_id)
            self.assertIsNotNone(item.part_number)

    def test_03_stock_groups(self):
        """Verify stock group retrieval returns StockGroup instances."""
        groups = self.provider.get_stock_groups()
        self.assertIsInstance(groups, list)
        for g in groups:
            self.assertIsInstance(g, StockGroup)

    def test_04_customer_retrieval(self):
        """Verify customer retrieval returns Customer domain objects."""
        cust = CustomerService.create_customer("Provider Test Client", 5.0, "27PROV1234P1Z1", "Net 30 Days")
        customers = self.provider.get_customers("Provider Test Client")
        self.assertIsInstance(customers, list)
        self.assertGreaterEqual(len(customers), 1)
        self.assertIsInstance(customers[0], Customer)
        self.assertEqual(customers[0].name, "Provider Test Client")

    def test_05_inventory_retrieval(self):
        """Verify inventory stock sheet retrieval."""
        inventory = self.provider.get_inventory()
        self.assertIsInstance(inventory, list)

    def test_06_ledger_retrieval(self):
        """Verify ledger history retrieval returns Ledger instances."""
        ledgers = self.provider.get_ledgers()
        self.assertIsInstance(ledgers, list)
        for l in ledgers:
            self.assertIsInstance(l, Ledger)

    def test_07_item_search(self):
        """Verify item search functionality."""
        items = self.provider.search_item("209")
        self.assertIsInstance(items, list)

    def test_08_invoice_creation(self):
        """Verify saving invoice through provider."""
        cust = CustomerService.create_customer("Provider Invoice Client", 10.0)
        items = self.provider.get_stock_items()
        if items:
            p_id = items[0].product_id
            order_id = OrderService.create_order(cust, [{"product_id": p_id, "quantity": 10}])
            inv_id = self.provider.save_invoice(order_id)
            self.assertIsNotNone(inv_id)

    def test_09_error_handling_missing_and_invalid_files(self):
        """Verify error handling on non-existent or corrupted files."""
        # 1. Missing File
        res_missing = self.provider.import_inventory("non_existent_file_path_999.xlsx")
        self.assertEqual(res_missing['status'], 'failed')
        self.assertGreater(len(res_missing['errors']), 0)
        
        # 2. Corrupt Binary Content
        corrupt_stream = BytesIO(b"Invalid raw binary content simulating bad file upload")
        res_corrupt = self.provider.import_inventory(corrupt_stream, filename="corrupt.xlsx")
        self.assertEqual(res_corrupt['status'], 'failed')
        self.assertGreater(len(res_corrupt['errors']), 0)

if __name__ == '__main__':
    unittest.main()
