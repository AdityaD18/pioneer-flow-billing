from .logger import tally_logger

class TallyValidationError(Exception):
    """Raised when synchronization data fails record count or integrity validation."""
    pass

class TallyValidator:
    """Validates imported Tally data dynamically against live Tally object counts."""

    @staticmethod
    def validate_stock_items(stock_items, expected_count=0, min_expected=100):
        actual_count = len(stock_items)
        tally_logger.info(f"🔍 Validating Stock Items: Imported {actual_count:,} items (Dynamic Expected: {expected_count:,}).")
        
        # Check against dynamic expected count if available
        if expected_count > 0 and actual_count < expected_count:
            msg = f"Validation Failed: Dynamic Expected Stock Count = {expected_count:,}, but imported {actual_count:,}!"
            tally_logger.error(f"❌ {msg}")
            raise TallyValidationError(msg)
            
        if expected_count == 0 and actual_count < min_expected:
            msg = f"Validation Failed: Expected at least {min_expected:,} Stock Items, but imported only {actual_count:,}!"
            tally_logger.error(f"❌ {msg}")
            raise TallyValidationError(msg)
            
        tally_logger.info(f"✅ Stock Items Validation Passed ({actual_count:,} items verified).")
        return True

    @staticmethod
    def validate_ledgers(ledgers, expected_count=0, min_expected=100):
        actual_count = len(ledgers)
        tally_logger.info(f"🔍 Validating Ledgers: Imported {actual_count:,} ledgers (Dynamic Expected: {expected_count:,}).")
        
        if expected_count > 0 and actual_count < expected_count:
            msg = f"Validation Failed: Dynamic Expected Ledger Count = {expected_count:,}, but imported {actual_count:,}!"
            tally_logger.error(f"❌ {msg}")
            raise TallyValidationError(msg)
            
        if expected_count == 0 and actual_count < min_expected:
            msg = f"Validation Failed: Expected at least {min_expected:,} Ledgers, but imported only {actual_count:,}!"
            tally_logger.error(f"❌ {msg}")
            raise TallyValidationError(msg)
            
        tally_logger.info(f"✅ Ledgers Validation Passed ({actual_count:,} ledgers verified).")
        return True
