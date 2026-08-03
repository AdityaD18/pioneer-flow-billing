import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tally.connection import TallyConnectionManager

class TestTallyConnectionManager(unittest.TestCase):
    def test_candidate_urls(self):
        candidates = TallyConnectionManager.get_candidate_urls("localhost", 9000)
        self.assertEqual(candidates[0], "http://127.0.0.1:9000")
        self.assertEqual(candidates[1], "http://localhost:9000")

    @patch("requests.get")
    @patch("requests.post")
    def test_get_health_probe_success(self, mock_post, mock_get):
        # Mock GET probe returning Tally server running response
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.text = "<RESPONSE>TallyPrime Server is Running</RESPONSE>"
        mock_get.return_value = mock_get_resp

        # Mock POST probe returning company XML
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.text = "<ENVELOPE><BODY><COMPANYNAME>Pioneer Automation</COMPANYNAME></BODY></ENVELOPE>"
        mock_post.return_value = mock_post_resp

        res = TallyConnectionManager.test_connection(host="127.0.0.1", port=9000, timeout=2)
        self.assertTrue(res["connected"])
        self.assertEqual(res["company_name"], "Pioneer Automation")
        self.assertEqual(res["endpoint"], "http://127.0.0.1:9000")
        self.assertIsNone(res["error_message"])

        # Verify GET request was executed first
        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args[0][0], "http://127.0.0.1:9000")

    @patch("requests.get")
    def test_get_health_probe_success_without_xml_post(self, mock_get):
        # Mock GET probe returning 200 OK, but POST fails
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.text = "<RESPONSE>TallyPrime Server is Running</RESPONSE>"
        mock_get.return_value = mock_get_resp

        with patch("requests.post", side_effect=Exception("XML Post Timeout")):
            res = TallyConnectionManager.test_connection(host="127.0.0.1", port=9000, timeout=2)
            self.assertTrue(res["connected"])
            self.assertEqual(res["company_name"], "Pioneer Automation")
            self.assertIsNone(res["error_message"])

    @patch("requests.get")
    def test_connection_refused_all_candidates(self, mock_get):
        mock_get.side_effect = Exception("Connection Refused")
        res = TallyConnectionManager.test_connection(host="localhost", port=9000, timeout=1)
        self.assertFalse(res["connected"])
        self.assertIn("Connection refused", res["error_message"])

if __name__ == '__main__':
    unittest.main()
