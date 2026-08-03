import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cache.sqlite_cache import ConnectorCacheDB
from tally.models.stock import TallyStockItem
from tally.models.ledger import TallyLedger

class TestConnectorCache(unittest.TestCase):
    def setUp(self):
        ConnectorCacheDB.init_cache_db()

    def test_stock_cache_upsert_and_retrieve(self):
        sample_item = TallyStockItem(
            guid="GUID-TEST-123",
            name="209-120",
            parent_group="209 Series",
            part_number="209-120",
            closing_balance=100.0,
            closing_rate=50.0,
            closing_value=5000.0
        )
        ConnectorCacheDB.save_stock_items([sample_item])
        items = ConnectorCacheDB.get_stock_items()
        self.assertGreaterEqual(len(items), 1)
        found = [i for i in items if i.part_number == "209-120"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].closing_balance, 100.0)

    def test_ledger_cache_upsert_and_retrieve(self):
        sample_ledger = TallyLedger(
            guid="GUID-LEDGER-99",
            name="Pioneer Automation Test Client",
            parent_group="Sundry Debtors",
            ledger_type="customer",
            closing_balance=15000.0,
            gstin="27AAACA9999F1Z0"
        )
        ConnectorCacheDB.save_ledgers([sample_ledger])
        customers = ConnectorCacheDB.get_ledgers(ledger_type="customer")
        self.assertGreaterEqual(len(customers), 1)
        found = [c for c in customers if c.name == "Pioneer Automation Test Client"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].gstin, "27AAACA9999F1Z0")

if __name__ == '__main__':
    unittest.main()
