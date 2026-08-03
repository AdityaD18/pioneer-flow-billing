import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from services.sync_engine import SyncEngine
from cache.sqlite_cache import ConnectorCacheDB
from tally.models.stock import TallyStockItem
from tally.models.ledger import TallyLedger

class TestSyncEngine(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        ConnectorCacheDB.init_cache_db()

    def test_sync_status_endpoint(self):
        response = self.client.get("/api/v1/sync/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)

    def test_commit_sync_transaction_atomic(self):
        stock_sample = [
            TallyStockItem(
                guid="SYNC-GUID-001",
                name="209-120",
                parent_group="209 Series",
                part_number="209-120",
                closing_balance=300.0,
                closing_rate=45.0,
                closing_value=13500.0
            )
        ]
        ledger_sample = [
            TallyLedger(
                guid="SYNC-LEDGER-001",
                name="Acme Sync Client",
                parent_group="Sundry Debtors",
                ledger_type="customer",
                closing_balance=5000.0
            )
        ]
        
        # Test atomic commit
        SyncEngine._commit_sync_transaction(stock_sample, [], ledger_sample, "full", "2026-08-03T15:26:00Z")
        
        cached_items = ConnectorCacheDB.get_stock_items()
        found_item = [i for i in cached_items if i.part_number == "209-120"]
        self.assertEqual(len(found_item), 1)
        self.assertEqual(found_item[0].closing_balance, 300.0)

        cached_ledgers = ConnectorCacheDB.get_ledgers(ledger_type="customer")
        found_ledger = [l for l in cached_ledgers if l.name == "Acme Sync Client"]
        self.assertEqual(len(found_ledger), 1)
        self.assertEqual(found_ledger[0].closing_balance, 5000.0)

if __name__ == '__main__':
    unittest.main()
