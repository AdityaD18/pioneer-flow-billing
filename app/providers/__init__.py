from app.providers.base_provider import BaseDataProvider
from app.providers.excel_provider import ExcelDataProvider

_current_provider = None

def get_data_provider() -> BaseDataProvider:
    """Returns the globally active Data Provider instance (defaults to ExcelDataProvider)."""
    global _current_provider
    if _current_provider is None:
        _current_provider = ExcelDataProvider()
    return _current_provider

def set_data_provider(provider: BaseDataProvider):
    """Sets or overrides the globally active Data Provider instance."""
    global _current_provider
    _current_provider = provider
