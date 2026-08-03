import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.providers.tally_provider import TallyDataProvider
from app.providers.connector_client import ConnectorClient
from app.models.domain import StockItem, Customer, Company

class TestOfflineBehaviour(unittest.TestCase):
    def setUp(self):
        # Create TallyDataProvider connected to unreachable mock client
        self.mock_client = MagicMock(spec=ConnectorClient)
        self.mock_client.get_stock.return_value = None
        self.mock_client.get_customers.return_value = None
        self.mock_client.get_company.return_value = None
        self.mock_client.get_inventory.return_value = None

        self.provider = TallyDataProvider(client=self.mock_client)

    def test_stock_retrieval_offline_fallback(self):
        """Verify get_stock_items returns local DB fallback without throwing exceptions when Connector is offline."""
        items = self.provider.get_stock_items()
        self.assertIsInstance(items, list)
        self.assertGreater(len(items), 0)
        self.assertIsInstance(items[0], StockItem)

    def test_customer_retrieval_offline_fallback(self):
        """Verify get_customers returns local DB fallback when Connector is offline."""
        customers = self.provider.get_customers()
        self.assertIsInstance(customers, list)

    def test_company_details_offline_fallback(self):
        """Verify get_company_details returns default Company model when Connector is offline."""
        company = self.provider.get_company_details()
        self.assertIsNotNone(company)
        self.assertIsInstance(company, Company)

    def test_inventory_retrieval_offline_fallback(self):
        """Verify get_inventory returns local DB fallback when Connector is offline."""
        inventory = self.provider.get_inventory()
        self.assertIsInstance(inventory, list)
        self.assertGreater(len(inventory), 0)

if __name__ == '__main__':
    unittest.main()
