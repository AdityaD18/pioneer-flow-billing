import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from services.ledger_service import LedgerService
from tally.models.ledger import TallyLedger

class TestLedgerRoutes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Mock cached ledgers for route testing
        LedgerService._cache_ledgers = [
            TallyLedger(
                guid="GUID-CUST-01",
                name="Acme Automation India Ltd",
                parent_group="Sundry Debtors",
                ledger_type="customer",
                closing_balance=12500.0,
                gstin="27AAACA1234F1Z1",
                address="Plot 42, MIDC Industrial Area, Pune",
                phone="020-27123456",
                email="contact@acmeauto.in"
            ),
            TallyLedger(
                guid="GUID-SUPP-01",
                name="WAGO India Pvt Ltd",
                parent_group="Sundry Creditors",
                ledger_type="supplier",
                closing_balance=45000.0,
                gstin="27AAACW9876F1Z0"
            )
        ]

    def test_get_all_ledgers(self):
        response = self.client.get("/api/v1/ledgers")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["total_records"], 2)

    def test_get_customers(self):
        response = self.client.get("/api/v1/customers")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Acme Automation India Ltd")

    def test_get_suppliers(self):
        response = self.client.get("/api/v1/suppliers")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "WAGO India Pvt Ltd")

if __name__ == '__main__':
    unittest.main()
