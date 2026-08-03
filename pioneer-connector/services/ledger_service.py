from datetime import datetime
from typing import List, Optional
import requests
from config.settings import settings
from tally.xml.xml_builder import TallyXMLBuilder
from tally.parser.xml_parser import TallyXMLParser
from tally.models.ledger import TallyLedger
from cache.sqlite_cache import ConnectorCacheDB

class LedgerService:
    """
    Service orchestrating Ledger directory synchronization with TallyPrime
    backed by SQLite cache for instant serving and offline resilience.
    """

    @classmethod
    def sync_ledgers(cls, force_refresh: bool = False) -> List[TallyLedger]:
        """
        Attempts to read from Tally. On success, validates & writes to SQLite cache.
        If Tally is unavailable or returns errors, serves cached data from SQLite seamlessly.
        """
        cached_ledgers = ConnectorCacheDB.get_ledgers()
        if cached_ledgers and not force_refresh:
            return cached_ledgers

        xml_request = TallyXMLBuilder.build_ledger_export_request(company_name=settings.TALLY_COMPANY)
        url = f"http://{settings.TALLY_HOST}:{settings.TALLY_PORT}"

        try:
            resp = requests.post(url, data=xml_request, headers={"Content-Type": "text/xml"}, timeout=settings.TALLY_TIMEOUT)
            if resp.status_code == 200:
                ledgers = TallyXMLParser.parse_ledgers(resp.text)
                if ledgers:
                    ConnectorCacheDB.save_ledgers(ledgers)
                    return ledgers
        except Exception:
            pass

        return cached_ledgers or ConnectorCacheDB.get_ledgers()

    @classmethod
    def get_customers(cls, force_refresh: bool = False) -> List[TallyLedger]:
        """Filters customer ledgers (Sundry Debtors) from cache or Tally."""
        ledgers = cls.sync_ledgers(force_refresh=force_refresh)
        return [l for l in ledgers if l.ledger_type == "customer"]

    @classmethod
    def get_suppliers(cls, force_refresh: bool = False) -> List[TallyLedger]:
        """Filters supplier ledgers (Sundry Creditors) from cache or Tally."""
        ledgers = cls.sync_ledgers(force_refresh=force_refresh)
        return [l for l in ledgers if l.ledger_type == "supplier"]

    @classmethod
    def get_last_sync_timestamp(cls) -> str:
        meta = ConnectorCacheDB.get_last_sync("ledgers")
        if meta and meta.get("last_sync_timestamp"):
            return meta["last_sync_timestamp"]
        return datetime.utcnow().isoformat() + "Z"
