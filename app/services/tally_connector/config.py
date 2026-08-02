import os
import json
from .logger import tally_logger

CONFIG_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config', 'tally_config.json'))

class TallyConfig:
    """Manages external configuration parameters for Pioneer Tally Connector."""

    DEFAULT_CONFIG = {
        "host": "localhost",
        "port": 9000,
        "username": "1",
        "password": "PtAc@6801",
        "timeout_seconds": 45,
        "max_retries": 3,
        "polling_interval_seconds": 30,
        "cache_db_path": "db/cache.db",
        "prod_db_path": "db/database.db",
        "log_file_path": "logs/tally_sync.log",
        "min_expected_stock_items": 1000,
        "min_expected_ledgers": 1000,
        "enable_deletion_detection": True
    }

    def __init__(self, config_path=CONFIG_FILE_PATH):
        self.config_path = config_path
        self._data = dict(self.DEFAULT_CONFIG)
        self.load()

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_data = json.load(f)
                    self._data.update(user_data)
                tally_logger.info(f"⚙️ Loaded Tally Configuration from {self.config_path}")
            except Exception as e:
                tally_logger.warning(f"⚠️ Failed to read config file {self.config_path}: {e}. Using defaults.")

    def get(self, key, default=None):
        return self._data.get(key, default if default is not None else self.DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self._data[key] = value
        self.save()

    def save(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2)

tally_config = TallyConfig()
