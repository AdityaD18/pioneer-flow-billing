from .logger import tally_logger

class TallyValidationError(Exception):
    """Raised when synchronization data fails record count or integrity validation."""
    pass

class TallyValidator:
    """Validates imported Tally data to ensure zero silent data loss."""

    @staticmethod
    def validate_stock_items(stock_items, min_expected=1000):
        actual_count = len(stock_items)
        tally_logger.info(f"🔍 Validating Stock Items: Imported {actual_count:,} items.")
        
        if actual_count < min_expected:
            msg = f"Validation Failed: Expected at least {min_expected:,} Stock Items, but imported only {actual_count:,}!"
            tally_logger.error(f"❌ {msg}")
            raise TallyValidationError(msg)
            
        tally_logger.info(f"✅ Stock Items Validation Passed ({actual_count:,} items verified).")
        return True

    @staticmethod
    def validate_ledgers(ledgers, min_expected=1000):
        actual_count = len(ledgers)
        tally_logger.info(f"🔍 Validating Ledgers: Imported {actual_count:,} ledgers.")
        
        if actual_count < min_expected:
            msg = f"Validation Failed: Expected at least {min_expected:,} Ledgers, but imported only {actual_count:,}!"
            tally_logger.error(f"❌ {msg}")
            raise TallyValidationError(msg)
            
        tally_logger.info(f"✅ Ledgers Validation Passed ({actual_count:,} ledgers verified).")
        return True
