import os
import sys

connector_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if connector_dir not in sys.path:
    sys.path.insert(0, connector_dir)

import unittest
from fastapi.testclient import TestClient
from main import app
from services.stock_service import StockService
from tally.models.stock import TallyStockItem

class TestStockRoutes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Mock cached stock items for route testing
        StockService._cache_items = [
            TallyStockItem(
                guid="GUID-001",
                name="209-120",
                parent_group="209 Series",
                part_number="209-120",
                closing_balance=500.0,
                closing_rate=45.0,
                closing_value=22500.0
            )
        ]

    def test_get_all_stock(self):
        response = self.client.get("/stock")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["total_records"], 1)
        self.assertEqual(data["items"][0]["part_number"], "209-120")

    def test_get_stock_by_id_success(self):
        response = self.client.get("/stock/209-120")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "209-120")

    def test_get_stock_by_id_not_found(self):
        response = self.client.get("/stock/NON-EXISTENT-PART")
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()
