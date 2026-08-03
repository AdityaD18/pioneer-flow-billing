import os
import pandas as pd
from io import BytesIO
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.quotation_repository import QuotationRepository
from app.core.logger import app_logger

class ExcelExportService:
    """Service handling generation of Excel export files and reports."""

    @classmethod
    def export_inventory_reorder_excel(cls):
        """Exports current inventory reorder status sheet to Excel BytesIO buffer."""
        app_logger.info("Generating Excel export for Inventory Reorder Status Sheet.")
        rows = InventoryRepository.get_stock_sheet()
        df = pd.DataFrame(rows)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Reorder Status', index=False)
        output.seek(0)
        return output.getvalue()

    @classmethod
    def export_invoices_excel(cls):
        """Exports invoice ledger history to Excel BytesIO buffer."""
        app_logger.info("Generating Excel export for Invoice History Ledger.")
        rows = InvoiceRepository.get_all()
        df = pd.DataFrame(rows)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Invoice History', index=False)
        output.seek(0)
        return output.getvalue()

    @classmethod
    def export_quotations_excel(cls):
        """Exports quotation ledger history to Excel BytesIO buffer."""
        app_logger.info("Generating Excel export for Quotation History Ledger.")
        rows = QuotationRepository.get_all()
        df = pd.DataFrame(rows)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Quotation History', index=False)
        output.seek(0)
        return output.getvalue()
