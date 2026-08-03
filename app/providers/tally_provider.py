import os
from typing import List, Optional, Dict, Any
from app.providers.base_provider import BaseDataProvider
from app.providers.connector_client import ConnectorClient
from app.providers.mappers import (
    StockMapper, CustomerMapper, LedgerMapper, CompanyMapper
)
from app.models.domain import (
    StockItem, StockGroup, Customer, Ledger,
    PurchaseOrder, SalesOrder, Company
)
from app.repositories.product_repository import ProductRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.quotation_repository import QuotationRepository
from app.services.import_service import ImportService
from app.services.invoice_service import InvoiceService
from app.services.excel_export_service import ExcelExportService
from app.core.config import Config

class TallyDataProvider(BaseDataProvider):
    """
    Tally Data Provider communicating exclusively via ConnectorClient & Mappers.
    Converts Connector REST JSON payloads into ERP canonical domain models.
    """

    def __init__(self, client: Optional[ConnectorClient] = None):
        self.client = client or ConnectorClient()

    def get_stock_items(self, search_kw: Optional[str] = None, series: Optional[str] = None) -> List[StockItem]:
        """Retrieves stock items via ConnectorClient and converts to StockItem domain models using StockMapper."""
        json_data = self.client.get_stock()
        if json_data and "items" in json_data:
            return StockMapper.to_domain_list(json_data["items"], search_kw=search_kw, series=series)

        # Fallback to local DB repository if Connector API is offline
        raw_list = ProductRepository.get_catalog(search_kw=search_kw, series=series)
        return [
            StockItem(
                product_id=r['product_id'],
                part_number=r['Part Number'],
                series=r['Series'],
                make=r['Make'],
                packing_quantity=r['Packing Qty'],
                current_stock=r['Current Stock (PCS)'],
                cost_price_100=r['Cost / 100 Pcs (INR)'],
                rate_per_unit=r['Rate / Pc (INR)']
            ) for r in raw_list
        ]

    def get_stock_groups(self) -> List[StockGroup]:
        """Retrieves stock groups via ConnectorClient and maps via StockMapper."""
        json_data = self.client.get_stock_groups()
        if json_data and isinstance(json_data, list):
            return [StockMapper.group_to_domain(g) for g in json_data]

        series_codes = ProductRepository.get_distinct_series()
        return [StockGroup(name=f"Series {s}", series_code=s) for s in series_codes]

    def get_customers(self, search_query: Optional[str] = None) -> List[Customer]:
        """Retrieves customer ledgers via ConnectorClient and maps via CustomerMapper."""
        json_data = self.client.get_customers()
        if json_data and isinstance(json_data, list):
            return CustomerMapper.to_domain_list(json_data, search_query=search_query)

        raw_custs = CustomerRepository.get_all(search_query=search_query)
        return [
            Customer(
                id=c['id'],
                name=c['name'],
                discount_percentage=c['discount_percentage'],
                gst_number=c['gst_number'],
                payment_terms=c['payment_terms'],
                created_at=c['created_at'],
                updated_at=c['updated_at']
            ) for c in raw_custs
        ]

    def get_ledgers(self) -> List[Ledger]:
        """Retrieves ledgers via ConnectorClient and maps via LedgerMapper."""
        json_data = self.client.get_ledgers()
        if json_data and "ledgers" in json_data:
            return LedgerMapper.to_domain_list(json_data["ledgers"])

        invoices = InvoiceRepository.get_all()
        quotations = QuotationRepository.get_all()
        ledger_entries = []
        for inv in invoices:
            ledger_entries.append(Ledger(
                id=inv['id'],
                name=f"Tax Invoice {inv['invoice_number']}",
                reference_number=inv['invoice_number'],
                customer_name=inv['customer_name_snapshot'],
                date=inv['invoice_date'],
                grand_total=inv['grand_total'],
                type="Invoice"
            ))
        for qtn in quotations:
            ledger_entries.append(Ledger(
                id=qtn['id'],
                name=f"Commercial Quotation {qtn['quotation_number']}",
                reference_number=qtn['quotation_number'],
                customer_name=qtn['customer_name_snapshot'],
                date=qtn['created_at'][:10],
                grand_total=qtn['grand_total'],
                type="Quotation"
            ))
        return ledger_entries

    def get_orders(self):
        return InvoiceRepository.get_all()

    def get_purchase_orders(self) -> List[PurchaseOrder]:
        """Retrieves purchase orders pending via ConnectorClient & StockMapper."""
        json_data = self.client.get_stock()
        if json_data and "items" in json_data:
            return StockMapper.to_purchase_order_list(json_data["items"])

        stock_sheet = InventoryRepository.get_stock_sheet()
        pos = []
        for r in stock_sheet:
            if r.get('Purc Orders Pending', 0) > 0:
                pos.append(PurchaseOrder(
                    part_number=r['Part Number'],
                    make=r['Make'],
                    purc_orders_pending=r['Purc Orders Pending'],
                    current_stock=r['Closing Stock'],
                    nett_available=r['Nett Available']
                ))
        return pos

    def get_sales_orders(self) -> List[SalesOrder]:
        """Retrieves sales orders due via ConnectorClient & StockMapper."""
        json_data = self.client.get_stock()
        if json_data and "items" in json_data:
            return StockMapper.to_sales_order_list(json_data["items"])

        stock_sheet = InventoryRepository.get_stock_sheet()
        sos = []
        for r in stock_sheet:
            if r.get('Sale Orders Due', 0) > 0:
                sos.append(SalesOrder(
                    part_number=r['Part Number'],
                    make=r['Make'],
                    sales_orders_due=r['Sale Orders Due'],
                    current_stock=r['Closing Stock'],
                    nett_available=r['Nett Available']
                ))
        return sos

    def get_inventory(self, search_query: Optional[str] = None, only_reorder: bool = False) -> List[dict]:
        """Retrieves inventory status sheet via ConnectorClient & StockMapper."""
        json_data = self.client.get_inventory()
        if json_data and "items" in json_data:
            return StockMapper.to_inventory_dict_list(json_data["items"], search_query=search_query, only_reorder=only_reorder)

        return InventoryRepository.get_stock_sheet(search_kw=search_query, only_reorder=only_reorder)

    def get_company_details(self) -> Company:
        """Retrieves company details via ConnectorClient & CompanyMapper."""
        json_data = self.client.get_company()
        if json_data:
            return CompanyMapper.to_domain(json_data)

        return Company(
            company_name=Config.COMPANY_NAME,
            company_subtitle=Config.COMPANY_SUBTITLE,
            company_footer=Config.COMPANY_FOOTER,
            default_gst_rate=Config.DEFAULT_GST_RATE,
            default_payment_terms=Config.DEFAULT_PAYMENT_TERMS
        )

    def save_invoice(self, order_id: int, invoice_date: Optional[str] = None) -> int:
        return InvoiceService.generate_invoice_for_order(order_id, invoice_date=invoice_date)

    def update_inventory(self, product_id: int, new_stock_qty: float) -> bool:
        InventoryRepository.update_stock(product_id, new_stock_qty)
        return True

    def search_item(self, query: str) -> List[StockItem]:
        return self.get_stock_items(search_kw=query)

    def import_inventory(self, file_path, sheet_name=None, filename='uploaded_file.xlsx', imported_by=None):
        return ImportService.import_inventory(file_path, sheet_name=sheet_name, filename=filename, imported_by=imported_by)

    def import_costs(self, file_path, sheet_name=None, filename='uploaded_file.xlsx', imported_by=None):
        return ImportService.import_costs(file_path, sheet_name=sheet_name, filename=filename, imported_by=imported_by)

    def sync_from_web_url(self, url, imported_by='Auto Sync'):
        return ImportService.sync_from_web_url(url, imported_by=imported_by)

    def export_inventory_reorder_excel(self):
        stock_rows = self.get_inventory()
        return ExcelExportService.generate_inventory_reorder_excel(stock_rows)

    def export_invoices_excel(self):
        invoices = InvoiceRepository.get_all()
        return ExcelExportService.generate_invoices_excel(invoices)

    def export_quotations_excel(self):
        quotations = QuotationRepository.get_all()
        return ExcelExportService.generate_quotations_excel(quotations)
