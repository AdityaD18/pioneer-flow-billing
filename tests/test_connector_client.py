import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.providers.connector_client import ConnectorClient

class TestConnectorClient(unittest.TestCase):
    def setUp(self):
        self.client = ConnectorClient(base_url="http://localhost:8000/api/v1", timeout=0.1, max_retries=1)

    @patch("requests.Session.request")
    def test_get_health_success(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "healthy", "tally_connected": True}
        mock_request.return_value = mock_resp

        result = self.client.get_health()
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "healthy")
        self.assertTrue(result["tally_connected"])

    @patch("requests.Session.request")
    def test_get_stock_success(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "success", "total_records": 1, "items": [{"part_number": "209-101"}]}
        mock_request.return_value = mock_resp

        result = self.client.get_stock()
        self.assertIsNotNone(result)
        self.assertEqual(result["total_records"], 1)

    @patch("requests.Session.request")
    def test_get_customers_success(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"name": "Acme Corp", "gstin": "27AAACA1234F1Z1"}]
        mock_request.return_value = mock_resp

        result = self.client.get_customers()
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Acme Corp")

    @patch("requests.Session.request")
    def test_network_failure_returns_none(self, mock_request):
        mock_request.side_effect = Exception("Connection Refused")
        result = self.client.get_stock()
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
