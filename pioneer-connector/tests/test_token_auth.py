import os
import sys
import unittest

connector_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if connector_dir not in sys.path:
    sys.path.insert(0, connector_dir)

from fastapi.testclient import TestClient
from main import app

class TestTokenAuth(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_register_device_and_token_refresh(self):
        # Register new device
        reg_resp = self.client.post("/device/register", json={"device_id": "DEV-TEST-123"})
        self.assertEqual(reg_resp.status_code, 200)
        reg_data = reg_resp.json()
        self.assertEqual(reg_data["status"], "success")
        self.assertEqual(reg_data["device_id"], "DEV-TEST-123")
        self.assertIn("access_token", reg_data)
        self.assertIn("refresh_token", reg_data)

        refresh_token = reg_data["refresh_token"]

        # Refresh token
        ref_resp = self.client.post("/device/token/refresh", headers={"X-Refresh-Token": refresh_token})
        self.assertEqual(ref_resp.status_code, 200)
        ref_data = ref_resp.json()
        self.assertIn("access_token", ref_data)

if __name__ == '__main__':
    unittest.main()
