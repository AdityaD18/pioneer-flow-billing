import os

# Base Directory Resolution
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Simple .env parser using stdlib
_env_vars = {}
env_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                _env_vars[key.strip()] = val.strip()

def _get_env(key, default):
    return os.environ.get(key, _env_vars.get(key, default))

class Config:
    """Centralized Application Configuration Class."""
    
    # System Metadata
    APP_NAME = _get_env('APP_NAME', 'Pioneer Flow Billing')
    APP_VERSION = _get_env('APP_VERSION', '1.0.0')
    APP_ENV = _get_env('APP_ENV', 'development')
    
    # Active Data Provider (Supported: 'excel' | Future: 'tally', 'postgres', 'api')
    DATA_PROVIDER = _get_env('DATA_PROVIDER', 'excel').lower()
    
    # Company Profile & Branding Defaults
    COMPANY_NAME = _get_env('COMPANY_NAME', 'Pioneer Flow Billing ERP')
    COMPANY_SUBTITLE = _get_env('COMPANY_SUBTITLE', 'Mechanical Parts Inventory Management & Automated Billing Engine')
    COMPANY_FOOTER = _get_env('COMPANY_FOOTER', 'Pioneer Automation Corp - Official Commercial Invoice')
    
    # Business Operational Defaults
    DEFAULT_GST_RATE = float(_get_env('DEFAULT_GST_RATE', '18.0'))
    DEFAULT_PAYMENT_TERMS = _get_env('DEFAULT_PAYMENT_TERMS', 'Net 30 Days')
    DEFAULT_MAKE = _get_env('DEFAULT_MAKE', 'WAGO')
    DEFAULT_UNIT = _get_env('DEFAULT_UNIT', 'PCS')
    
    # Directory & File Storage Paths
    DATABASE_DIR = os.path.abspath(os.path.join(BASE_DIR, 'instance'))
    DATABASE_PATH = os.path.abspath(os.path.join(DATABASE_DIR, _get_env('DATABASE_PATH', 'pioneer_flow.db')))
    SCHEMA_PATH = os.path.abspath(os.path.join(BASE_DIR, 'app', 'database', 'schema.sql'))
    
    EXPORTS_DIR = os.path.abspath(os.path.join(BASE_DIR, _get_env('EXPORTS_DIR', 'exports')))
    UPLOADS_DIR = os.path.abspath(os.path.join(BASE_DIR, _get_env('UPLOADS_DIR', 'uploads')))
    LOGS_DIR = os.path.abspath(os.path.join(BASE_DIR, _get_env('LOGS_DIR', 'logs')))
    
    # Reference Source Spreadsheet Locations
    STOCK_SOURCE_PATH = os.path.abspath(os.path.join(BASE_DIR, _get_env('STOCK_EXCEL_PATH', 'group order status.xlsx')))
    COST_SOURCE_PATH = os.path.abspath(os.path.join(BASE_DIR, _get_env('COST_EXCEL_PATH', 'cost_data.xlsx')))
    
    # Aliases for backward compatibility
    STOCK_EXCEL_PATH = STOCK_SOURCE_PATH
    COST_EXCEL_PATH = COST_SOURCE_PATH
    
    @classmethod
    def ensure_directories(cls):
        """Creates required runtime directories if they do not exist."""
        for d in [cls.DATABASE_DIR, cls.EXPORTS_DIR, cls.UPLOADS_DIR, cls.LOGS_DIR]:
            os.makedirs(d, exist_ok=True)

# Ensure runtime directories exist upon config load
Config.ensure_directories()
