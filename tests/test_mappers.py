import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.providers.mappers import StockMapper, CustomerMapper, LedgerMapper, CompanyMapper
from app.models.domain import StockItem, Customer, Ledger, Company, StockGroup

class TestMappers(unittest.TestCase):
    def test_stock_mapper(self):
        raw_json = {
            "guid": "GUID-209-101",
            "name": "WAGO 209-101",
            "part_number": "209-101",
            "parent_group": "209",
            "closing_balance": 500.0,
            "closing_rate": 12.50
        }
        item = StockMapper.to_domain(raw_json)
        self.assertIsInstance(item, StockItem)
        self.assertEqual(item.product_id, "GUID-209-101")
        self.assertEqual(item.part_number, "209-101")
        self.assertEqual(item.current_stock, 500.0)
        self.assertEqual(item.rate_per_unit, 12.50)

    def test_customer_mapper(self):
        raw_json = {
            "name": "Acme Automation India Ltd",
            "gstin": "27AAACA1234F1Z1",
            "payment_terms": "Net 30 Days"
        }
        customer = CustomerMapper.to_domain(raw_json, index=1)
        self.assertIsInstance(customer, Customer)
        self.assertEqual(customer.id, 1)
        self.assertEqual(customer.name, "Acme Automation India Ltd")
        self.assertEqual(customer.gst_number, "27AAACA1234F1Z1")

    def test_ledger_mapper(self):
        raw_json = {
            "guid": "GUID-LEDG-01",
            "name": "Sales Accounts",
            "ledger_type": "income",
            "closing_balance": 150000.0,
            "updated_at": "2026-08-01T10:00:00Z"
        }
        ledger = LedgerMapper.to_domain(raw_json, index=5)
        self.assertIsInstance(ledger, Ledger)
        self.assertEqual(ledger.id, 5)
        self.assertEqual(ledger.name, "Sales Accounts")
        self.assertEqual(ledger.type, "Income")

    def test_company_mapper(self):
        raw_json = {
            "company_name": "Pioneer Electrical Systems",
            "gstin": "27AAACP1234F1Z9"
        }
        company = CompanyMapper.to_domain(raw_json)
        self.assertIsInstance(company, Company)
        self.assertEqual(company.company_name, "Pioneer Electrical Systems")

if __name__ == '__main__':
    unittest.main()
