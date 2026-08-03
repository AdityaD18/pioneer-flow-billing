import os
import sys

connector_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if connector_dir not in sys.path:
    sys.path.insert(0, connector_dir)

import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from cache.sqlite_cache import ConnectorCacheDB
from cache.models import CanonicalLedger

class TestLedgerRoutes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Use isolated test DB for cache tests
        self.test_db_path = "test_ledger_cache.db"
        self.cache_patcher = patch("cache.sqlite_cache.ConnectorCacheDB.db_path", self.test_db_path)
        self.cache_patcher.start()
        
        self.cache = ConnectorCacheDB(db_path=self.test_db_path)
        self.cache.clear_all()
        self._seed_data()

    def tearDown(self):
        self.cache_patcher.stop()
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    def _seed_data(self):
        self.cache.save_ledgers([
            CanonicalLedger(
                guid="LEDGER-001",
                name="Acme Automation India Ltd",
                parent_group="Sundry Debtors",
                ledger_type="customer",
                closing_balance=125000.0,
                gstin="27AAACA1234F1Z1",
                state_name="Maharashtra"
            ),
            CanonicalLedger(
                guid="LEDGER-002",
                name="WAGO India Pvt Ltd",
                parent_group="Sundry Creditors",
                ledger_type="supplier",
                closing_balance=45000.0,
                gstin="27AAACW9876F1Z0"
            )
        ])

    def test_get_all_ledgers(self):
        response = self.client.get("/ledgers")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["total_records"], 2)

    def test_get_customers(self):
        response = self.client.get("/customers")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Acme Automation India Ltd")

    def test_get_suppliers(self):
        response = self.client.get("/suppliers")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "WAGO India Pvt Ltd")

if __name__ == '__main__':
    unittest.main()
