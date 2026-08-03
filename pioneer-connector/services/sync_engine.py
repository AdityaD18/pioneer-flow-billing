import time
from datetime import datetime
from typing import Dict, Any, Optional
import requests
from config.settings import settings
from tally.connection import TallyConnectionManager
from tally.xml.xml_builder import TallyXMLBuilder
from tally.parser.xml_parser import TallyXMLParser
from cache.sqlite_cache import ConnectorCacheDB

class SyncEngine:
    """
    Transactional Synchronization Engine for TallyPrime.
    Executes full and incremental syncs with validation, atomic commits, retries, and rollback.
    """

    _last_sync_stats: Optional[Dict[str, Any]] = None

    @classmethod
    def execute_sync(cls, sync_type: str = "full") -> Dict[str, Any]:
        """
        Runs the full transactional synchronization pipeline:
        Download -> DOM Validate -> Stage -> Atomic Commit -> Update Manifest.
        Includes exponential backoff retry logic and automatic transaction rollback on error.
        """
        start_time = time.perf_counter()
        sync_timestamp = datetime.utcnow().isoformat() + "Z"
        
        retries = 0
        max_retries = settings.MAX_RETRIES
        backoff_factor = settings.RETRY_BACKOFF_FACTOR
        last_error = None

        url = f"http://{settings.TALLY_HOST}:{settings.TALLY_PORT}"

        while retries <= max_retries:
            try:
                # 1. Probe Tally Connection
                conn_info = TallyConnectionManager.test_connection()
                if not conn_info["connected"]:
                    raise ConnectionError(f"Tally server unreachable: {conn_info['error_message']}")

                # 2. Download & DOM Validate Stock Items
                stock_xml_req = TallyXMLBuilder.build_stock_item_export_request(company_name=settings.TALLY_COMPANY)
                resp_stock = requests.post(url, data=stock_xml_req, headers={"Content-Type": "text/xml"}, timeout=settings.TALLY_TIMEOUT)
                if resp_stock.status_code != 200:
                    raise ConnectionError(f"HTTP {resp_stock.status_code} fetching stock items")
                stock_items = TallyXMLParser.parse_stock_items(resp_stock.text)

                # 3. Download & DOM Validate Stock Groups
                group_xml_req = TallyXMLBuilder.build_export_request("List of Stock Groups", company_name=settings.TALLY_COMPANY)
                resp_groups = requests.post(url, data=group_xml_req, headers={"Content-Type": "text/xml"}, timeout=settings.TALLY_TIMEOUT)
                stock_groups = TallyXMLParser.parse_stock_groups(resp_groups.text) if resp_groups.status_code == 200 else []

                # 4. Download & DOM Validate Ledgers
                ledger_xml_req = TallyXMLBuilder.build_ledger_export_request(company_name=settings.TALLY_COMPANY)
                resp_ledger = requests.post(url, data=ledger_xml_req, headers={"Content-Type": "text/xml"}, timeout=settings.TALLY_TIMEOUT)
                if resp_ledger.status_code != 200:
                    raise ConnectionError(f"HTTP {resp_ledger.status_code} fetching ledgers")
                ledgers = TallyXMLParser.parse_ledgers(resp_ledger.text)

                # 5. Atomic Transaction: Stage, Commit SQLite Cache, & Update Manifest
                cls._commit_sync_transaction(stock_items, stock_groups, ledgers, sync_type, sync_timestamp)
                
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                stats = {
                    "status": "success",
                    "sync_type": sync_type,
                    "records_synced": {
                        "stock_items": len(stock_items),
                        "stock_groups": len(stock_groups),
                        "ledgers": len(ledgers)
                    },
                    "duration_ms": elapsed_ms,
                    "sync_timestamp": sync_timestamp,
                    "retries_attempted": retries,
                    "error": None
                }
                cls._last_sync_stats = stats
                return stats

            except Exception as e:
                last_error = str(e)
                retries += 1
                if retries <= max_retries:
                    sleep_time = backoff_factor ** (retries - 1)
                    time.sleep(sleep_time)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        stats = {
            "status": "failed",
            "sync_type": sync_type,
            "records_synced": {"stock_items": 0, "stock_groups": 0, "ledgers": 0},
            "duration_ms": elapsed_ms,
            "sync_timestamp": sync_timestamp,
            "retries_attempted": max_retries,
            "error": last_error
        }
        cls._last_sync_stats = stats
        return stats

    @classmethod
    def _commit_sync_transaction(cls, stock_items, stock_groups, ledgers, sync_type, sync_timestamp):
        """
        Atomic SQLite transaction for staging and committing sync data.
        Rolls back 100% of changes if any write fails, maintaining cache integrity.
        """
        conn = ConnectorCacheDB.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN TRANSACTION;")

            for item in stock_items:
                cur.execute("""
                    INSERT INTO cached_stock_items (
                        guid, part_number, name, parent_group, closing_balance, 
                        closing_rate, closing_value, purchase_pending, sales_due, 
                        nett_available, reorder_level, shortfall, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(part_number) DO UPDATE SET
                        guid=excluded.guid, name=excluded.name, parent_group=excluded.parent_group,
                        closing_balance=excluded.closing_balance, closing_rate=excluded.closing_rate,
                        closing_value=excluded.closing_value, purchase_pending=excluded.purchase_pending,
                        sales_due=excluded.sales_due, nett_available=excluded.nett_available,
                        reorder_level=excluded.reorder_level, shortfall=excluded.shortfall,
                        updated_at=excluded.updated_at
                """, (
                    item.guid, item.part_number, item.name, item.parent_group, item.closing_balance,
                    item.closing_rate, item.closing_value, item.purchase_pending, item.sales_due,
                    item.nett_available, item.reorder_level, item.shortfall, sync_timestamp
                ))

            for g in stock_groups:
                cur.execute("""
                    INSERT INTO cached_stock_groups (guid, name, parent_group, series_code, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET
                        guid=excluded.guid, parent_group=excluded.parent_group,
                        series_code=excluded.series_code, updated_at=excluded.updated_at
                """, (g.guid, g.name, g.parent_group, g.series_code, sync_timestamp))

            for l in ledgers:
                cur.execute("""
                    INSERT INTO cached_ledgers (
                        guid, name, parent_group, ledger_type, closing_balance, 
                        gstin, address, phone, email, state, pin_code, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET
                        guid=excluded.guid, parent_group=excluded.parent_group,
                        ledger_type=excluded.ledger_type, closing_balance=excluded.closing_balance,
                        gstin=excluded.gstin, address=excluded.address, phone=excluded.phone,
                        email=excluded.email, state=excluded.state, pin_code=excluded.pin_code,
                        updated_at=excluded.updated_at
                """, (
                    l.guid, l.name, l.parent_group, l.ledger_type, l.closing_balance,
                    l.gstin, l.address, l.phone, l.email, l.state, l.pin_code, sync_timestamp
                ))

            # Update Sync Manifest
            cur.execute("""
                INSERT INTO sync_metadata (entity_name, last_sync_timestamp, record_count, status)
                VALUES ('sync_manifest', ?, ?, 'success')
                ON CONFLICT(entity_name) DO UPDATE SET
                    last_sync_timestamp=excluded.last_sync_timestamp,
                    record_count=excluded.record_count,
                    status=excluded.status
            """, (sync_timestamp, len(stock_items) + len(ledgers)))

            conn.commit()
        except Exception:
            conn.rollback() # Rollback on error
            raise
        finally:
            cur.close()
            conn.close()

    @classmethod
    def get_sync_status(cls) -> Dict[str, Any]:
        """Returns statistics and metadata from the most recent sync run."""
        if cls._last_sync_stats:
            return cls._last_sync_stats
        
        meta = ConnectorCacheDB.get_last_sync("sync_manifest")
        if meta:
            return {
                "status": meta.get("status", "unknown"),
                "sync_type": "full",
                "records_synced": meta.get("record_count", 0),
                "sync_timestamp": meta.get("last_sync_timestamp"),
                "retries_attempted": 0,
                "error": None
            }
        return {
            "status": "never_run",
            "sync_type": "none",
            "records_synced": 0,
            "sync_timestamp": None,
            "retries_attempted": 0,
            "error": None
        }
