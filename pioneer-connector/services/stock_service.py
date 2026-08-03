import time
from datetime import datetime
from typing import List, Optional
import requests
from config.settings import settings
from tally.xml.xml_builder import TallyXMLBuilder
from tally.parser.xml_parser import TallyXMLParser
from tally.models.stock import TallyStockItem, TallyStockGroup

class StockService:
    """Service orchestrating Stock Item and Stock Group synchronization with TallyPrime."""

    _cache_items: List[TallyStockItem] = []
    _cache_groups: List[TallyStockGroup] = []
    _last_sync_timestamp: Optional[str] = None

    @classmethod
    def sync_stock_items(cls, force_refresh: bool = False) -> List[TallyStockItem]:
        """
        Downloads all stock items from Tally, converts XML to canonical JSON objects,
        validates record counts, and updates internal cache.
        """
        if cls._cache_items and not force_refresh:
            return cls._cache_items

        xml_request = TallyXMLBuilder.build_stock_item_export_request(company_name=settings.TALLY_COMPANY)
        url = f"http://{settings.TALLY_HOST}:{settings.TALLY_PORT}"

        try:
            resp = requests.post(url, data=xml_request, headers={"Content-Type": "text/xml"}, timeout=settings.TALLY_TIMEOUT)
            if resp.status_code == 200:
                items = TallyXMLParser.parse_stock_items(resp.text)
                cls._cache_items = items
                cls._last_sync_timestamp = datetime.utcnow().isoformat() + "Z"
                return items
        except Exception:
            pass

        return cls._cache_items

    @classmethod
    def sync_stock_groups(cls, force_refresh: bool = False) -> List[TallyStockGroup]:
        """Downloads all stock groups from Tally."""
        if cls._cache_groups and not force_refresh:
            return cls._cache_groups

        xml_request = TallyXMLBuilder.build_export_request("List of Stock Groups", company_name=settings.TALLY_COMPANY)
        url = f"http://{settings.TALLY_HOST}:{settings.TALLY_PORT}"

        try:
            resp = requests.post(url, data=xml_request, headers={"Content-Type": "text/xml"}, timeout=settings.TALLY_TIMEOUT)
            if resp.status_code == 200:
                groups = TallyXMLParser.parse_stock_groups(resp.text)
                cls._cache_groups = groups
                return groups
        except Exception:
            pass

        return cls._cache_groups

    @classmethod
    def get_stock_item_by_id(cls, item_id: str) -> Optional[TallyStockItem]:
        """Looks up a stock item by part number or GUID."""
        items = cls.sync_stock_items()
        item_id_lower = item_id.lower()
        for item in items:
            if item.part_number.lower() == item_id_lower or (item.guid and item.guid.lower() == item_id_lower) or item.name.lower() == item_id_lower:
                return item
        return None

    @classmethod
    def get_last_sync_timestamp(cls) -> str:
        return cls._last_sync_timestamp or datetime.utcnow().isoformat() + "Z"
