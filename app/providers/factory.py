from typing import Dict, Type
from app.providers.base_provider import BaseDataProvider
from app.providers.excel_provider import ExcelDataProvider
from app.core.logger import app_logger

class ProviderFactory:
    """Factory managing source-agnostic Data Provider instances for Pioneer Flow Billing."""
    
    _registry: Dict[str, Type[BaseDataProvider]] = {
        "excel": ExcelDataProvider
    }
    _instances: Dict[str, BaseDataProvider] = {}
    _active_provider_name: str = "excel"

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseDataProvider]):
        """Registers a new Data Provider class with the factory."""
        cls._registry[name.lower()] = provider_class
        app_logger.info(f"Registered Data Provider '{name.lower()}' ({provider_class.__name__}).")

    @classmethod
    def set_active_provider(cls, name: str):
        """Sets the globally active Data Provider type."""
        name_clean = name.lower()
        if name_clean not in cls._registry:
            raise ValueError(f"Provider '{name}' is not registered with ProviderFactory. Available: {list(cls._registry.keys())}")
        cls._active_provider_name = name_clean
        app_logger.info(f"Set active Data Provider to '{name_clean}'.")

    @classmethod
    def get_provider(cls, name: str = None) -> BaseDataProvider:
        """
        Obtains a Data Provider instance.
        If no name is specified, returns the currently active Data Provider.
        """
        provider_name = (name or cls._active_provider_name).lower()
        
        if provider_name not in cls._registry:
            raise ValueError(f"Provider '{provider_name}' is not registered with ProviderFactory.")
            
        if provider_name not in cls._instances:
            provider_class = cls._registry[provider_name]
            cls._instances[provider_name] = provider_class()
            app_logger.info(f"Instantiated singleton Data Provider '{provider_name}' ({provider_class.__name__}).")
            
        return cls._instances[provider_name]
