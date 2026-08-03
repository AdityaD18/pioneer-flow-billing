import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ui.views.sync_dashboard import render_sync_dashboard_tab

class TestSyncDashboard(unittest.TestCase):
    def test_sync_dashboard_import_and_callable(self):
        """Verify render_sync_dashboard_tab is importable and callable without syntax errors."""
        self.assertTrue(callable(render_sync_dashboard_tab))

if __name__ == '__main__':
    unittest.main()
