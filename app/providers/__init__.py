from app.providers.base_provider import BaseDataProvider
from app.providers.factory import ProviderFactory

def get_data_provider() -> BaseDataProvider:
    """Returns the globally active Data Provider obtained via ProviderFactory."""
    return ProviderFactory.get_provider()

def set_data_provider(provider: BaseDataProvider):
    """Overrides active provider instance."""
    ProviderFactory.set_active_provider("excel")

__all__ = ["BaseDataProvider", "ProviderFactory", "get_data_provider", "set_data_provider"]
