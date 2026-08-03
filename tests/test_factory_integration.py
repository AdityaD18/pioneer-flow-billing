import os
import sys
import unittest
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.providers import get_data_provider, ProviderFactory
from app.providers.excel_provider import ExcelDataProvider
from app.providers.tally_provider import TallyDataProvider
from app.core.config import Config

class TestProviderFactoryIntegration(unittest.TestCase):
    def setUp(self):
        # Reset factory singleton instances for clean isolation
        ProviderFactory._instances = {}

    @patch.object(Config, 'DATA_PROVIDER', 'excel')
    def test_factory_instantiates_excel_provider(self):
        provider = ProviderFactory.get_provider()
        self.assertIsInstance(provider, ExcelDataProvider)

    @patch.object(Config, 'DATA_PROVIDER', 'tally')
    def test_factory_instantiates_tally_provider(self):
        provider = ProviderFactory.get_provider()
        self.assertIsInstance(provider, TallyDataProvider)

    @patch.object(Config, 'DATA_PROVIDER', 'invalid_provider_type')
    def test_factory_fallback_to_excel(self):
        provider = ProviderFactory.get_provider()
        self.assertIsInstance(provider, ExcelDataProvider)

    def test_explicit_provider_selection(self):
        excel_prov = ProviderFactory.get_provider('excel')
        self.assertIsInstance(excel_prov, ExcelDataProvider)

        tally_prov = ProviderFactory.get_provider('tally')
        self.assertIsInstance(tally_prov, TallyDataProvider)

if __name__ == '__main__':
    unittest.main()
