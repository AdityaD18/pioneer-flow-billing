import os
import sys
import unittest

connector_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if connector_dir not in sys.path:
    sys.path.insert(0, connector_dir)

from fastapi.testclient import TestClient
from main import app

class TestVersionCapabilities(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_version_endpoint(self):
        response = self.client.get("/version")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], "2.0.1")
        self.assertEqual(data["protocol"], 1)

    def test_capabilities_endpoint(self):
        response = self.client.get("/capabilities")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["stock"])
        self.assertTrue(data["ledgers"])
        self.assertTrue(data["incremental_sync"])

    def test_identity_endpoint(self):
        response = self.client.get("/identity")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("device_id", data)
        self.assertIn("computer_name", data)
        self.assertIn("connector_version", data)

    def test_enhanced_health_readiness_diagnostics(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["healthy"])
        self.assertIn("ready", data)
        self.assertIn("tally_connected", data)
        self.assertIn("queue_size", data)

if __name__ == '__main__':
    unittest.main()
