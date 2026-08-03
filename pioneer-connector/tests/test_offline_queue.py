import os
import sys
import unittest

connector_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if connector_dir not in sys.path:
    sys.path.insert(0, connector_dir)

from cache.offline_queue import enqueue_payload, get_offline_queue_size, fetch_and_clear_queue, init_queue_db

class TestOfflineQueue(unittest.TestCase):
    def setUp(self):
        init_queue_db()
        fetch_and_clear_queue() # Start clean

    def test_enqueue_and_clear_queue(self):
        self.assertEqual(get_offline_queue_size(), 0)

        sample_payload = {"items": [{"part_number": "209-120", "qty": 10}]}
        success = enqueue_payload("stock_sync", sample_payload)
        self.assertTrue(success)
        self.assertEqual(get_offline_queue_size(), 1)

        items = fetch_and_clear_queue()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["payload_type"], "stock_sync")
        self.assertEqual(items[0]["payload_data"], sample_payload)

        # Queue cleared
        self.assertEqual(get_offline_queue_size(), 0)

if __name__ == '__main__':
    unittest.main()
