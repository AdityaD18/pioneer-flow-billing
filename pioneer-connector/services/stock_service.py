from datetime import datetime
from typing import List, Optional
import requests
from config.settings import settings
from tally.xml.xml_builder import TallyXMLBuilder
from tally.parser.xml_parser import TallyXMLParser
from tally.models.stock import TallyStockItem, TallyStockGroup
from cache.sqlite_cache import ConnectorCacheDB

class StockService:
    """
    Service orchestrating Stock Item and Stock Group synchronization with TallyPrime
    backed by SQLite cache for instant serving and offline resilience.
    """

    @classmethod
    def sync_stock_items(cls, force_refresh: bool = False) -> List[TallyStockItem]:
        """
        Attempts to read from Tally. On success, validates & writes to SQLite cache.
        If Tally is unavailable or returns errors, serves cached data from SQLite seamlessly.
        """
        cached_items = ConnectorCacheDB.get_stock_items()

        # If cached data exists and force_refresh is False, return cached instantly
        if cached_items and not force_refresh:
            return cached_items

        xml_request = TallyXMLBuilder.build_stock_item_export_request(company_name=settings.TALLY_COMPANY)
        url = f"http://{settings.TALLY_HOST}:{settings.TALLY_PORT}"

        try:
            resp = requests.post(url, data=xml_request, headers={"Content-Type": "text/xml"}, timeout=settings.TALLY_TIMEOUT)
            if resp.status_code == 200:
                items = TallyXMLParser.parse_stock_items(resp.text)
                if items:
                    ConnectorCacheDB.save_stock_items(items)
                    return items
        except Exception:
            # Fall back to SQLite cache when Tally is offline
            pass

        return cached_items or ConnectorCacheDB.get_stock_items()

    @classmethod
    def sync_stock_groups(cls, force_refresh: bool = False) -> List[TallyStockGroup]:
        """Downloads stock groups from Tally, writes to SQLite cache, or serves cached."""
        cached_groups = ConnectorCacheDB.get_stock_groups()
        if cached_groups and not force_refresh:
            return cached_groups

        xml_request = TallyXMLBuilder.build_export_request("List of Stock Groups", company_name=settings.TALLY_COMPANY)
        url = f"http://{settings.TALLY_HOST}:{settings.TALLY_PORT}"

        try:
            resp = requests.post(url, data=xml_request, headers={"Content-Type": "text/xml"}, timeout=settings.TALLY_TIMEOUT)
            if resp.status_code == 200:
                groups = TallyXMLParser.parse_stock_groups(resp.text)
                if groups:
                    ConnectorCacheDB.save_stock_groups(groups)
                    return groups
        except Exception:
            pass

        return cached_groups or ConnectorCacheDB.get_stock_groups()

    @classmethod
    def get_stock_item_by_id(cls, item_id: str) -> Optional[TallyStockItem]:
        """Looks up a stock item by part number or GUID from cache."""
        items = cls.sync_stock_items()
        item_id_lower = item_id.lower()
        for item in items:
            if item.part_number.lower() == item_id_lower or (item.guid and item.guid.lower() == item_id_lower) or item.name.lower() == item_id_lower:
                return item
        return None

    @classmethod
    def get_last_sync_timestamp(cls) -> str:
        meta = ConnectorCacheDB.get_last_sync("stock_items")
        if meta and meta.get("last_sync_timestamp"):
            return meta["last_sync_timestamp"]
        return datetime.utcnow().isoformat() + "Z"
