from app.providers.base_provider import BaseDataProvider
from app.repositories.product_repository import ProductRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.quotation_repository import QuotationRepository
from app.services.import_service import ImportService
from app.services.invoice_service import InvoiceService
from app.core.config import Config
from app.core.constants import EXCEL_STOCK_SHEET_NAME, EXCEL_COST_SHEET_NAME

class ExcelDataProvider(BaseDataProvider):
    """Excel & Local Database Data Provider implementation."""

    def get_stock_items(self, search_kw=None, series=None):
        return ProductRepository.get_catalog(search_kw=search_kw, series=series)

    def get_stock_groups(self):
        return ProductRepository.get_distinct_series()

    def get_customers(self, search_query=None):
        return CustomerRepository.get_all(search_query=search_query)

    def get_ledgers(self):
        invoices = InvoiceRepository.get_all()
        quotations = QuotationRepository.get_all()
        return {
            "invoices": invoices,
            "quotations": quotations
        }

    def get_orders(self):
        return InvoiceRepository.get_all()

    def get_purchase_orders(self):
        stock_sheet = InventoryRepository.get_stock_sheet()
        return [r for r in stock_sheet if r.get('Purc Orders Pending', 0) > 0]

    def get_sales_orders(self):
        stock_sheet = InventoryRepository.get_stock_sheet()
        return [r for r in stock_sheet if r.get('Sale Orders Due', 0) > 0]

    def get_inventory(self, search_query=None, only_reorder=False):
        return InventoryRepository.get_stock_sheet(search_kw=search_query, only_reorder=only_reorder)

    def get_company_details(self):
        return {
            "company_name": Config.COMPANY_NAME,
            "company_subtitle": Config.COMPANY_SUBTITLE,
            "company_footer": Config.COMPANY_FOOTER,
            "default_gst_rate": Config.DEFAULT_GST_RATE,
            "default_payment_terms": Config.DEFAULT_PAYMENT_TERMS
        }

    def save_invoice(self, order_id, invoice_date=None):
        return InvoiceService.generate_invoice_for_order(order_id, invoice_date=invoice_date)

    def update_inventory(self, product_id, new_stock_qty):
        InventoryRepository.update_stock(product_id, new_stock_qty)

    def search_item(self, query):
        return ProductRepository.get_catalog(search_kw=query)

    def import_inventory(self, file_path, sheet_name=EXCEL_STOCK_SHEET_NAME, filename='uploaded_file.xlsx', imported_by=None):
        return ImportService.import_inventory(file_path, sheet_name=sheet_name, filename=filename, imported_by=imported_by)

    def import_costs(self, file_path, sheet_name=EXCEL_COST_SHEET_NAME, filename='uploaded_file.xlsx', imported_by=None):
        return ImportService.import_costs(file_path, sheet_name=sheet_name, filename=filename, imported_by=imported_by)

    def sync_from_web_url(self, url, imported_by='Auto Sync'):
        return ImportService.sync_from_web_url(url, imported_by=imported_by)
