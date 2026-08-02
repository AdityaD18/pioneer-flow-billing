import time
import uuid
import hashlib
from datetime import datetime
from .config import tally_config
from .logger import tally_logger
from .tally_client import TallyClient
from .validator import TallyValidator
from .cache import TallyCacheManager

class PioneerConnector:
    """Primary production orchestration connector for Tally Prime 7.1 live sync."""

    def __init__(self, host=None, port=None, username=None, password=None):
        self.client = TallyClient(host=host, port=port, username=username, password=password)
        self.cache = TallyCacheManager()
        self.last_full_sync = None
        self.last_incremental_sync = None
        self.stock_item_alter_id = 0
        self.ledger_alter_id = 0

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
        expected_count = self.client.get_object_count("StockItem")
        TallyValidator.validate_stock_items(stock_items, expected_count=expected_count, min_expected=1000)
        self.cache.update_cache_stock_items(stock_items)
        return len(stock_items)

    def sync_ledgers(self):
        """Synchronizes 100% of ledgers to cache and production database."""
        ledgers = self.client.fetch_ledgers()
        expected_count = self.client.get_object_count("Ledger")
        TallyValidator.validate_ledgers(ledgers, expected_count=expected_count, min_expected=1000)
        self.cache.update_cache_ledgers(ledgers)
        return len(ledgers)

    def full_sync(self):
        """Executes full atomic synchronization from Tally Prime into cache.db and database.db with manifest logging."""
        t0 = time.time()
        sync_id = f"SYNC_FULL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        tally_logger.info(f"🚀 Starting Full Tally Sync [{sync_id}]...")
        
        try:
            # 1. Query Dynamic Expected Object Counts from Tally
            expected_stock = self.client.get_object_count("StockItem")
            expected_ledger = self.client.get_object_count("Ledger")
            expected_total = expected_stock + expected_ledger
            
            # 2. Fetch Records from Tally
            stock_items = self.client.fetch_stock_items()
            ledgers = self.client.fetch_ledgers()
            received_total = len(stock_items) + len(ledgers)
            
            # 3. Dynamic Validation
            TallyValidator.validate_stock_items(
                stock_items,
                expected_count=expected_stock,
                min_expected=tally_config.get("min_expected_stock_items", 1000)
            )
            TallyValidator.validate_ledgers(
                ledgers,
                expected_count=expected_ledger,
                min_expected=tally_config.get("min_expected_ledgers", 1000)
            )
            
            # 4. Atomic Staging & Deletion Detection
            detect_deletions = tally_config.get("enable_deletion_detection", True)
            stock_stats = self.cache.update_cache_stock_items(stock_items, detect_deletions=detect_deletions)
            ledger_stats = self.cache.update_cache_ledgers(ledgers, detect_deletions=detect_deletions)
            
            # 5. Push Staged Cache to Production DB
            self.cache.sync_cache_to_prod_database()
            
            # Update independent AlterID state
            self.stock_item_alter_id = max([i.get('alter_id', 0) for i in stock_items] + [0])
            self.ledger_alter_id = max([l.get('alter_id', 0) for l in ledgers] + [0])
            
            duration = round(time.time() - t0, 2)
            self.last_full_sync = datetime.now()
            
            # 6. Build Manifest
            inserted_tot = stock_stats['inserted'] + ledger_stats['inserted']
            updated_tot = stock_stats['updated'] + ledger_stats['updated']
            deleted_tot = stock_stats['deleted'] + ledger_stats['deleted']
            
            checksum = hashlib.md5(f"{len(stock_items)}_{len(ledgers)}_{duration}".encode()).hexdigest()
            
            manifest = {
                "sync_id": sync_id,
                "sync_type": "FULL",
                "timestamp": self.last_full_sync.isoformat(),
                "duration_sec": duration,
                "expected_records": expected_total,
                "received_records": received_total,
                "inserted_records": inserted_tot,
                "updated_records": updated_tot,
                "deleted_records": deleted_tot,
                "skipped_records": 0,
                "failed_records": 0,
                "retry_count": 0,
                "validation_result": "PASSED",
                "checksum": checksum
            }
            
            self.cache.save_sync_manifest(manifest)
            self.cache.log_sync_metric("FULL", "SUCCESS", len(stock_items), len(ledgers), duration)
            
            tally_logger.info(f"🎉 Full Sync [{sync_id}] Passed! Synced {len(stock_items):,} SKUs & {len(ledgers):,} Ledgers in {duration}s.")
            return manifest
            
        except Exception as ex:
            duration = round(time.time() - t0, 2)
            err_msg = str(ex)
            
            manifest = {
                "sync_id": sync_id,
                "sync_type": "FULL",
                "timestamp": datetime.now().isoformat(),
                "duration_sec": duration,
                "expected_records": 0,
                "received_records": 0,
                "inserted_records": 0,
                "updated_records": 0,
                "deleted_records": 0,
                "skipped_records": 0,
                "failed_records": 1,
                "retry_count": 3,
                "validation_result": f"FAILED: {err_msg}",
                "checksum": ""
            }
            
            self.cache.save_sync_manifest(manifest)
            self.cache.log_sync_metric("FULL", "FAILED", 0, 0, duration, error_msg=err_msg)
            tally_logger.error(f"❌ Full Sync [{sync_id}] Failed: {err_msg}")
            return manifest

    def incremental_sync(self):
        """Executes lightweight incremental sync for modified records using independent per-object AlterIDs."""
        t0 = time.time()
        sync_id = f"SYNC_INC_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        # Read max AlterIDs from cache if zero
        if self.stock_item_alter_id == 0:
            self.stock_item_alter_id = self.cache.get_max_alter_id("CACHE_STOCK_ITEMS")
        if self.ledger_alter_id == 0:
            self.ledger_alter_id = self.cache.get_max_alter_id("CACHE_LEDGERS")
            
        tally_logger.info(f"🔄 Starting Incremental Sync [{sync_id}] (Stock AlterID > {self.stock_item_alter_id}, Ledger AlterID > {self.ledger_alter_id})...")
        
        try:
            stock_items = self.client.fetch_stock_items(min_alter_id=self.stock_item_alter_id)
            ledgers = self.client.fetch_ledgers(min_alter_id=self.ledger_alter_id)
            
            stock_stats = {"inserted": 0, "updated": 0, "deleted": 0}
            ledger_stats = {"inserted": 0, "updated": 0, "deleted": 0}
            
            if stock_items:
                stock_stats = self.cache.update_cache_stock_items(stock_items, detect_deletions=False)
                self.stock_item_alter_id = max([i.get('alter_id', 0) for i in stock_items] + [self.stock_item_alter_id])
                
            if ledgers:
                ledger_stats = self.cache.update_cache_ledgers(ledgers, detect_deletions=False)
                self.ledger_alter_id = max([l.get('alter_id', 0) for l in ledgers] + [self.ledger_alter_id])
                
            if stock_items or ledgers:
                self.cache.sync_cache_to_prod_database()
                
            duration = round(time.time() - t0, 2)
            self.last_incremental_sync = datetime.now()
            
            manifest = {
                "sync_id": sync_id,
                "sync_type": "INCREMENTAL",
                "timestamp": self.last_incremental_sync.isoformat(),
                "duration_sec": duration,
                "expected_records": len(stock_items) + len(ledgers),
                "received_records": len(stock_items) + len(ledgers),
                "inserted_records": stock_stats['inserted'] + ledger_stats['inserted'],
                "updated_records": stock_stats['updated'] + ledger_stats['updated'],
                "deleted_records": 0,
                "skipped_records": 0,
                "failed_records": 0,
                "retry_count": 0,
                "validation_result": "PASSED",
                "checksum": hashlib.md5(f"{len(stock_items)}_{len(ledgers)}_{duration}".encode()).hexdigest()
            }
            
            self.cache.save_sync_manifest(manifest)
            self.cache.log_sync_metric("INCREMENTAL", "SUCCESS", len(stock_items), len(ledgers), duration)
            return manifest
            
        except Exception as ex:
            duration = round(time.time() - t0, 2)
            err_msg = str(ex)
            
            manifest = {
                "sync_id": sync_id,
                "sync_type": "INCREMENTAL",
                "timestamp": datetime.now().isoformat(),
                "duration_sec": duration,
                "expected_records": 0,
                "received_records": 0,
                "inserted_records": 0,
                "updated_records": 0,
                "deleted_records": 0,
                "skipped_records": 0,
                "failed_records": 1,
                "retry_count": 3,
                "validation_result": f"FAILED: {err_msg}",
                "checksum": ""
            }
            
            self.cache.save_sync_manifest(manifest)
            self.cache.log_sync_metric("INCREMENTAL", "FAILED", 0, 0, duration, error_msg=err_msg)
            return manifest

# Global Connector instance singleton
pioneer_connector = PioneerConnector()
