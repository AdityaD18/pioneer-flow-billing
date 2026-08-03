import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ENV_FILE_PATH = os.path.join(BASE_DIR, '.env')

def load_env_vars():
    """Lightweight parser for .env key-value file."""
    env_dict = {}
    if os.path.exists(ENV_FILE_PATH):
        try:
            with open(ENV_FILE_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        env_dict[k.strip()] = v.strip()
        except Exception:
            pass
    return env_dict

_env_vars = load_env_vars()

class Config:
    """Centralized System Configuration Engine."""

    BASE_DIR = BASE_DIR
    APP_NAME = os.environ.get('APP_NAME') or _env_vars.get('APP_NAME', 'Pioneer Flow Billing ERP')
    APP_VERSION = os.environ.get('APP_VERSION') or _env_vars.get('APP_VERSION', '1.0.0')
    APP_ENV = os.environ.get('APP_ENV') or _env_vars.get('APP_ENV', 'production')

    # Path Configurations
    rel_db_path = os.environ.get('DATABASE_PATH') or _env_vars.get('DATABASE_PATH', 'db/database.db')
    DATABASE_PATH = os.path.abspath(os.path.join(BASE_DIR, rel_db_path))
    DATABASE_DIR = os.path.dirname(DATABASE_PATH)
    SCHEMA_PATH = os.path.abspath(os.path.join(BASE_DIR, 'app', 'database', 'schema.sql'))

    EXPORTS_DIR = os.path.abspath(os.path.join(BASE_DIR, _env_vars.get('EXPORTS_DIR', 'exports')))
    UPLOADS_DIR = os.path.abspath(os.path.join(BASE_DIR, _env_vars.get('UPLOADS_DIR', 'uploads')))
    LOGS_DIR = os.path.abspath(os.path.join(BASE_DIR, _env_vars.get('LOGS_DIR', 'logs')))

    STOCK_EXCEL_PATH = os.path.abspath(os.path.join(BASE_DIR, _env_vars.get('STOCK_EXCEL_PATH', 'group order status.xlsx')))
    COST_EXCEL_PATH = os.path.abspath(os.path.join(BASE_DIR, _env_vars.get('COST_EXCEL_PATH', 'cost_data.xlsx')))

    # Company & Business Defaults
    COMPANY_NAME = _env_vars.get('COMPANY_NAME', 'PIONEER AUTOMATION')
    COMPANY_SUBTITLE = _env_vars.get('COMPANY_SUBTITLE', 'Mechanical & Industrial Billing Solutions')
    COMPANY_FOOTER = _env_vars.get('COMPANY_FOOTER', 'Thank you for your business! | Pioneer Automation Corp')
    
    DEFAULT_GST_RATE = float(_env_vars.get('DEFAULT_GST_RATE', 18.0))
    DEFAULT_PAYMENT_TERMS = _env_vars.get('DEFAULT_PAYMENT_TERMS', 'Net 30 Days')
    DEFAULT_MAKE = _env_vars.get('DEFAULT_MAKE', 'WAGO')
    DEFAULT_UNIT = _env_vars.get('DEFAULT_UNIT', 'PCS')

# Ensure directories exist
os.makedirs(Config.DATABASE_DIR, exist_ok=True)
os.makedirs(Config.EXPORTS_DIR, exist_ok=True)
os.makedirs(Config.UPLOADS_DIR, exist_ok=True)
os.makedirs(Config.LOGS_DIR, exist_ok=True)
