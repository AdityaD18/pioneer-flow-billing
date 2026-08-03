from fastapi import APIRouter, Query
from typing import List
from services.ledger_service import LedgerService
from tally.models.ledger import TallyLedger, LedgerSyncResponse

router = APIRouter(tags=["Ledger & Customer Directory Synchronization"])

@router.get("/ledgers", response_model=LedgerSyncResponse)
def get_all_ledgers(force_refresh: bool = Query(False, description="Force live sync from Tally")):
    """Retrieves all Tally ledgers (customers, suppliers, expenses, income) in normalized JSON format."""
    ledgers = LedgerService.sync_ledgers(force_refresh=force_refresh)
    return LedgerSyncResponse(
        status="success",
        total_records=len(ledgers),
        ledgers=ledgers,
        sync_timestamp=LedgerService.get_last_sync_timestamp()
    )

@router.get("/customers", response_model=List[TallyLedger])
def get_customers(force_refresh: bool = Query(False, description="Force live sync from Tally")):
    """Retrieves all customer ledgers (Sundry Debtors) in normalized JSON format."""
    return LedgerService.get_customers(force_refresh=force_refresh)

@router.get("/suppliers", response_model=List[TallyLedger])
def get_suppliers(force_refresh: bool = Query(False, description="Force live sync from Tally")):
    """Retrieves all supplier ledgers (Sundry Creditors) in normalized JSON format."""
    return LedgerService.get_suppliers(force_refresh=force_refresh)
