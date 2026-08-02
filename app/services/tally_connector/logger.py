import os
import logging

LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'logs'))
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOGS_DIR, 'tally_sync.log')

def get_tally_logger(name="TallyConnector"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        # File handler
        fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
    return logger

tally_logger = get_tally_logger()
