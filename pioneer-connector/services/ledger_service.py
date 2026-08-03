import time
from datetime import datetime
from typing import List, Optional
import requests
from config.settings import settings
from tally.xml.xml_builder import TallyXMLBuilder
from tally.parser.xml_parser import TallyXMLParser
from tally.models.ledger import TallyLedger

class LedgerService:
    """Service orchestrating Ledger directory synchronization with TallyPrime."""

    _cache_ledgers: List[TallyLedger] = []
    _last_sync_timestamp: Optional[str] = None

    @classmethod
    def sync_ledgers(cls, force_refresh: bool = False) -> List[TallyLedger]:
        """
        Downloads all ledgers from Tally, converts XML to canonical JSON objects,
        and updates internal cache.
        """
        if cls._cache_ledgers and not force_refresh:
            return cls._cache_ledgers

        xml_request = TallyXMLBuilder.build_ledger_export_request(company_name=settings.TALLY_COMPANY)
        url = f"http://{settings.TALLY_HOST}:{settings.TALLY_PORT}"

        try:
            resp = requests.post(url, data=xml_request, headers={"Content-Type": "text/xml"}, timeout=settings.TALLY_TIMEOUT)
            if resp.status_code == 200:
                ledgers = TallyXMLParser.parse_ledgers(resp.text)
                cls._cache_ledgers = ledgers
                cls._last_sync_timestamp = datetime.utcnow().isoformat() + "Z"
                return ledgers
        except Exception:
            pass

        return cls._cache_ledgers

    @classmethod
    def get_customers(cls, force_refresh: bool = False) -> List[TallyLedger]:
        """Filters customer ledgers (Sundry Debtors)."""
        ledgers = cls.sync_ledgers(force_refresh=force_refresh)
        return [l for l in ledgers if l.ledger_type == "customer"]

    @classmethod
    def get_suppliers(cls, force_refresh: bool = False) -> List[TallyLedger]:
        """Filters supplier ledgers (Sundry Creditors)."""
        ledgers = cls.sync_ledgers(force_refresh=force_refresh)
        return [l for l in ledgers if l.ledger_type == "supplier"]

    @classmethod
    def get_last_sync_timestamp(cls) -> str:
        return cls._last_sync_timestamp or datetime.utcnow().isoformat() + "Z"
