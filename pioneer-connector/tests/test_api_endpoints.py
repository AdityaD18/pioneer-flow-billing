import os
import sys
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from cache.sqlite_cache import ConnectorCacheDB
from tally.models.stock import TallyStockItem, TallyStockGroup
from tally.models.ledger import TallyLedger

class TestConnectorAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        ConnectorCacheDB.init_cache_db()
        
        # Seed mock cache data into SQLite
        ConnectorCacheDB.save_stock_items([
            TallyStockItem(
                guid="GUID-REST-01",
                name="209-120",
                parent_group="209 Series",
                part_number="209-120",
                closing_balance=100.0
            )
        ])
        ConnectorCacheDB.save_stock_groups([
            TallyStockGroup(guid="GUID-GRP-01", name="209 Series", series_code="209")
        ])
        ConnectorCacheDB.save_ledgers([
            TallyLedger(
                guid="GUID-CUST-01",
                name="Pioneer Automation Client",
                parent_group="Sundry Debtors",
                ledger_type="customer"
            )
        ])

    def test_01_health_endpoint(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertIn("tally_health", res.json())

    def test_02_company_endpoint(self):
        res = self.client.get("/company")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("company_name", data)
        self.assertIn("tally_version", data)

    def test_03_stock_endpoint(self):
        res = self.client.get("/stock")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["total_records"], 1)

    def test_04_stock_groups_endpoint(self):
        res = self.client.get("/stock/groups")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(len(data), 1)

    def test_05_customers_endpoint(self):
        res = self.client.get("/customers")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(len(data), 1)

    def test_06_ledgers_endpoint(self):
        res = self.client.get("/ledgers")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")

    def test_07_sync_status_endpoint(self):
        res = self.client.get("/sync/status")
        self.assertEqual(res.status_code, 200)
        self.assertIn("status", res.json())

    @patch("services.sync_engine.SyncEngine.execute_sync")
    def test_08_sync_full_endpoint(self, mock_sync):
        mock_sync.return_value = {"status": "success", "sync_type": "full", "duration_ms": 15.0}
        res = self.client.post("/sync/full")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")

    @patch("services.sync_engine.SyncEngine.execute_sync")
    def test_09_sync_incremental_endpoint(self, mock_sync):
        mock_sync.return_value = {"status": "success", "sync_type": "incremental", "duration_ms": 10.0}
        res = self.client.post("/sync/incremental")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")

if __name__ == '__main__':
    unittest.main()
