from typing import Dict, Type
from app.providers.base_provider import BaseDataProvider
from app.providers.excel_provider import ExcelDataProvider
from app.core.config import Config
from app.core.logger import app_logger

class ProviderFactory:
    """Factory managing source-agnostic Data Provider instances driven by configuration."""
    
    _registry: Dict[str, Type[BaseDataProvider]] = {
        "excel": ExcelDataProvider
    }
    _instances: Dict[str, BaseDataProvider] = {}

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseDataProvider]):
        """Registers a new Data Provider class with the factory."""
        cls._registry[name.lower()] = provider_class
        app_logger.info(f"Registered Data Provider '{name.lower()}' ({provider_class.__name__}).")

    @classmethod
    def get_configured_provider_name(cls) -> str:
        """Reads the configured DATA_PROVIDER setting from Config."""
        return Config.DATA_PROVIDER.lower()

    @classmethod
    def get_provider(cls, name: str = None) -> BaseDataProvider:
        """
        Obtains a Data Provider instance.
        If no name is specified, reads from Config.DATA_PROVIDER.
        Falls back to 'excel' if an unregistered provider type is requested.
        """
        provider_name = (name or cls.get_configured_provider_name()).lower()
        
        if provider_name not in cls._registry:
            app_logger.warning(
                f"Requested provider '{provider_name}' is not currently registered. "
                f"Available: {list(cls._registry.keys())}. Falling back to default 'excel' provider."
            )
            provider_name = "excel"
            
        if provider_name not in cls._instances:
            provider_class = cls._registry[provider_name]
            cls._instances[provider_name] = provider_class()
            app_logger.info(f"Instantiated singleton Data Provider '{provider_name}' ({provider_class.__name__}).")
            
        return cls._instances[provider_name]
