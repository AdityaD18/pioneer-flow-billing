import time
from datetime import datetime
from .logger import tally_logger
from .tally_client import TallyClient
from .validator import TallyValidator
from .cache import TallyCacheManager

class PioneerConnector:
    """Primary production orchestration connector for Tally Prime 7.1 live sync."""

    def __init__(self, host="localhost", port=9000, username="1", password="PtAc@6801"):
        self.client = TallyClient(host=host, port=port, username=username, password=password)
        self.cache = TallyCacheManager()
        self.last_full_sync = None
        self.last_incremental_sync = None

    def check_connection(self):
        """Returns True if Tally Prime is active and reachable."""
        return self.client.is_connected()

    def get_active_company(self):
        """Returns the active company name in Tally Prime."""
        return self.client.get_active_company()

    def get_stock_items(self):
        """Returns parsed stock items from Tally."""
        return self.client.fetch_stock_items()

    def get_ledgers(self):
        """Returns parsed ledgers from Tally."""
        return self.client.fetch_ledgers()

    def get_stock_groups(self):
        """Returns parsed stock groups from Tally."""
        return self.client.fetch_stock_groups()

    def sync_stock(self):
        """Synchronizes 100% of stock items to cache and production database."""
        stock_items = self.client.fetch_stock_items()
        TallyValidator.validate_stock_items(stock_items, min_expected=1000)
        self.cache.update_cache_stock_items(stock_items)
        return len(stock_items)

    def sync_ledgers(self):
        """Synchronizes 100% of ledgers to cache and production database."""
        ledgers = self.client.fetch_ledgers()
        TallyValidator.validate_ledgers(ledgers, min_expected=1000)
        self.cache.update_cache_ledgers(ledgers)
        return len(ledgers)

    def full_sync(self):
        """Executes full complete synchronization from Tally Prime into cache.db and database.db."""
        t0 = time.time()
        tally_logger.info("🚀 Starting Full Tally Prime Synchronization...")
        
        try:
            # 1. Fetch & Validate
            stock_items = self.client.fetch_stock_items()
            ledgers = self.client.fetch_ledgers()
            
            TallyValidator.validate_stock_items(stock_items, min_expected=1000)
            TallyValidator.validate_ledgers(ledgers, min_expected=1000)
            
            # 2. Update Cache
            self.cache.update_cache_stock_items(stock_items)
            self.cache.update_cache_ledgers(ledgers)
            
            # 3. Push to Main Database
            res = self.cache.sync_cache_to_prod_database()
            
            duration = round(time.time() - t0, 2)
            self.last_full_sync = datetime.now()
            
            self.cache.log_sync_metric(
                sync_type="FULL",
                status="SUCCESS",
                stock_count=len(stock_items),
                ledger_count=len(ledgers),
                duration_sec=duration
            )
            
            tally_logger.info(f"🎉 Full Sync Complete in {duration}s! Synced {len(stock_items):,} stock items & {len(ledgers):,} ledgers.")
            
            return {
                "status": "success",
                "stock_count": len(stock_items),
                "ledger_count": len(ledgers),
                "duration_sec": duration,
                "timestamp": self.last_full_sync.isoformat()
            }
        except Exception as ex:
            duration = round(time.time() - t0, 2)
            err_msg = str(ex)
            self.cache.log_sync_metric(
                sync_type="FULL",
                status="FAILED",
                stock_count=0,
                ledger_count=0,
                duration_sec=duration,
                error_msg=err_msg
            )
            tally_logger.error(f"❌ Full Sync Failed: {err_msg}")
            return {
                "status": "failed",
                "stock_count": 0,
                "ledger_count": 0,
                "duration_sec": duration,
                "error": err_msg
            }

    def incremental_sync(self):
        """Executes lightweight incremental sync for modified records."""
        t0 = time.time()
        max_alter_id = self.cache.get_max_alter_id("CACHE_STOCK_ITEMS")
        tally_logger.info(f"🔄 Starting Incremental Sync (AlterID > {max_alter_id})...")
        
        try:
            stock_items = self.client.fetch_stock_items(min_alter_id=max_alter_id if max_alter_id > 0 else None)
            ledgers = self.client.fetch_ledgers(min_alter_id=max_alter_id if max_alter_id > 0 else None)
            
            if stock_items:
                self.cache.update_cache_stock_items(stock_items)
            if ledgers:
                self.cache.update_cache_ledgers(ledgers)
                
            if stock_items or ledgers:
                self.cache.sync_cache_to_prod_database()
                
            duration = round(time.time() - t0, 2)
            self.last_incremental_sync = datetime.now()
            
            self.cache.log_sync_metric(
                sync_type="INCREMENTAL",
                status="SUCCESS",
                stock_count=len(stock_items),
                ledger_count=len(ledgers),
                duration_sec=duration
            )
            
            return {
                "status": "success",
                "stock_count": len(stock_items),
                "ledger_count": len(ledgers),
                "duration_sec": duration,
                "timestamp": self.last_incremental_sync.isoformat()
            }
        except Exception as ex:
            duration = round(time.time() - t0, 2)
            err_msg = str(ex)
            self.cache.log_sync_metric(
                sync_type="INCREMENTAL",
                status="FAILED",
                stock_count=0,
                ledger_count=0,
                duration_sec=duration,
                error_msg=err_msg
            )
            return {
                "status": "failed",
                "stock_count": 0,
                "ledger_count": 0,
                "duration_sec": duration,
                "error": err_msg
            }

# Global Connector instance singleton
pioneer_connector = PioneerConnector()
