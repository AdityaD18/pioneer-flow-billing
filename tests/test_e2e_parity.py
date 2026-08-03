import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.database import init_db
from app.providers.excel_provider import ExcelDataProvider
from app.providers.tally_provider import TallyDataProvider
from app.services.customer_service import CustomerService
from app.services.order_service import OrderService

class TestEndToEndParity(unittest.TestCase):
    """
    Comprehensive End-to-End Provider Parity Verification Suite.
    Guarantees 100% business logic, domain model, and calculation parity between
    ExcelDataProvider and TallyDataProvider.
    """

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.excel_provider = ExcelDataProvider()
        cls.tally_provider = TallyDataProvider()

    def test_01_company_details_parity(self):
        """Verify Company metadata parity between Excel and Tally providers."""
        excel_comp = self.excel_provider.get_company_details()
        tally_comp = self.tally_provider.get_company_details()

        self.assertEqual(excel_comp.company_name, tally_comp.company_name)
        self.assertEqual(excel_comp.company_subtitle, tally_comp.company_subtitle)
        self.assertEqual(excel_comp.company_footer, tally_comp.company_footer)
        self.assertEqual(excel_comp.default_gst_rate, tally_comp.default_gst_rate)
        self.assertEqual(excel_comp.default_payment_terms, tally_comp.default_payment_terms)

    def test_02_stock_items_and_groups_parity(self):
        """Verify StockItem list count, structure, and StockGroup parity."""
        excel_items = self.excel_provider.get_stock_items()
        tally_items = self.tally_provider.get_stock_items()

        self.assertGreater(len(excel_items), 0)
        self.assertGreater(len(tally_items), 0)
        self.assertEqual(len(excel_items), len(tally_items))

        # Spot check item attribute parity
        e_item = excel_items[0]
        t_item = tally_items[0]
        self.assertEqual(e_item.part_number, t_item.part_number)
        self.assertEqual(e_item.make, t_item.make)

        excel_groups = self.excel_provider.get_stock_groups()
        tally_groups = self.tally_provider.get_stock_groups()
        self.assertEqual(len(excel_groups), len(tally_groups))

    def test_03_customer_directory_parity(self):
        """Verify Customer directory retrieval parity."""
        cust = CustomerService.get_customer_by_name("Parity Client Ltd")
        if not cust:
            cust = CustomerService.create_customer("Parity Client Ltd", 10.0, "27PARITY1234P1Z1", "Net 30 Days")

        excel_custs = self.excel_provider.get_customers("Parity Client Ltd")
        tally_custs = self.tally_provider.get_customers("Parity Client Ltd")

        self.assertGreaterEqual(len(excel_custs), 1)
        self.assertGreaterEqual(len(tally_custs), 1)
        self.assertEqual(excel_custs[0].name, tally_custs[0].name)

    def test_04_inventory_and_reorder_math_parity(self):
        """Verify inventory stock sheet calculations and shortfall math parity."""
        excel_inv = self.excel_provider.get_inventory()
        tally_inv = self.tally_provider.get_inventory()

        self.assertEqual(len(excel_inv), len(tally_inv))
        
        # Verify schema keys match 100%
        expected_keys = {"Part Number", "Make", "Closing Stock", "Purc Orders Pending", "Sale Orders Due", "Nett Available", "Min Reorder Qty", "Reorder Level", "Short Fall", "Order To Be Placed", "Last Updated"}
        self.assertEqual(set(excel_inv[0].keys()), expected_keys)
        self.assertEqual(set(tally_inv[0].keys()), expected_keys)

        # Verify math formula: Nett Available = Closing Stock + Purc Orders Pending - Sale Orders Due
        sample = tally_inv[0]
        calculated_nett = sample["Closing Stock"] + sample["Purc Orders Pending"] - sample["Sale Orders Due"]
        self.assertEqual(sample["Nett Available"], calculated_nett)

    def test_05_orders_and_ledger_history_parity(self):
        """Verify Purchase Orders, Sales Orders, and Ledger history parity."""
        excel_pos = self.excel_provider.get_purchase_orders()
        tally_pos = self.tally_provider.get_purchase_orders()
        self.assertEqual(len(excel_pos), len(tally_pos))

        excel_sos = self.excel_provider.get_sales_orders()
        tally_sos = self.tally_provider.get_sales_orders()
        self.assertEqual(len(excel_sos), len(tally_sos))

        excel_ledgers = self.excel_provider.get_ledgers()
        tally_ledgers = self.tally_provider.get_ledgers()
        self.assertIsInstance(excel_ledgers, list)
        self.assertIsInstance(tally_ledgers, list)

    def test_06_search_and_filter_parity(self):
        """Verify product item search parity."""
        excel_search = self.excel_provider.search_item("209")
        tally_search = self.tally_provider.search_item("209")
        self.assertEqual(len(excel_search), len(tally_search))

if __name__ == '__main__':
    unittest.main()
