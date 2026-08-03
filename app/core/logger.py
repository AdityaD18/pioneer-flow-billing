import os
import sys
import logging
from app.core.config import Config

# Ensure logs directory exists
os.makedirs(Config.LOGS_DIR, exist_ok=True)
LOG_FILE_PATH = os.path.join(Config.LOGS_DIR, 'app.log')

# Create Root Logger for Pioneer Flow Billing
logger = logging.getLogger("pioneer_billing")
logger.setLevel(logging.INFO)

# Prevent duplicate handlers if module is reloaded
if not logger.handlers:
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | [%(name)s] | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File Handler
    file_handler = logging.FileHandler(LOG_FILE_PATH, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

# Specialized Logger Instances
app_logger = logging.getLogger("pioneer_billing.app")
db_logger = logging.getLogger("pioneer_billing.database")
import_logger = logging.getLogger("pioneer_billing.import")
billing_logger = logging.getLogger("pioneer_billing.billing")
