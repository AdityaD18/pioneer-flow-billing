from app.repositories.product_repository import ProductRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.quotation_repository import QuotationRepository
from app.repositories.customer_repository import CustomerRepository

class ReportsService:
    """Service handling high-level reporting metrics and dashboard KPI summaries."""

    @classmethod
    def get_dashboard_summary_metrics(cls):
        """Calculates key summary statistics for UI dashboard headers."""
        catalog_products = ProductRepository.get_catalog()
        stock_rows = InventoryRepository.get_stock_sheet()
        invoices = InvoiceRepository.get_all()
        quotations = QuotationRepository.get_all()
        customers = CustomerRepository.get_all()
        
        total_products = len(catalog_products)
        low_stock_items = len([r for r in stock_rows if r.get('Short Fall', 0) > 0 or r.get('Order To Be Placed', 0) > 0])
        total_invoices = len(invoices)
        total_quotations = len(quotations)
        total_customers = len(customers)
        
        total_revenue = sum(float(i.get('grand_total', 0) or 0) for i in invoices)
        
        return {
            "total_products": total_products,
            "low_stock_items": low_stock_items,
            "total_invoices": total_invoices,
            "total_quotations": total_quotations,
            "total_customers": total_customers,
            "total_revenue": round(total_revenue, 2)
        }
