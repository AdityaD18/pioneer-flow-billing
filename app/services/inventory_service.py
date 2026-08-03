from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_repository import ProductRepository
from app.core.logger import app_logger

class InventoryService:
    """Service handling stock levels, inventory math, and reorder status calculations."""

    @staticmethod
    def calculate_reorder_metrics(stock_val, purc_val, sales_val, reorder_val=0.0, min_reorder_val=0.0, nett_raw=None, shortfall_raw=None, order_to_place_raw=None):
        """Calculates derived inventory metrics based on stock, pending orders, and reorder levels."""
        if nett_raw is not None:
            nett_val = nett_raw
        else:
            nett_val = stock_val + purc_val - sales_val
            
        if shortfall_raw is not None:
            shortfall_val = shortfall_raw
        else:
            shortfall_val = max(0.0, reorder_val - nett_val)
            
        if order_to_place_raw is not None:
            order_to_place_val = order_to_place_raw
        else:
            order_to_place_val = max(shortfall_val, min_reorder_val) if shortfall_val > 0 else 0.0
            
        return {
            "nett_available": nett_val,
            "shortfall": shortfall_val,
            "order_to_place": order_to_place_val
        }

    @classmethod
    def update_product_stock(cls, product_id, new_stock_qty):
        """Updates stock quantity for a product."""
        app_logger.info(f"Updating stock for product ID {product_id} to {new_stock_qty} PCS.")
        InventoryRepository.update_stock(product_id, new_stock_qty)

    @classmethod
    def get_reorder_status_sheet(cls, search_query=None, only_reorder=False):
        """Retrieves stock group reorder status sheet records."""
        return InventoryRepository.get_stock_sheet(search_kw=search_query, only_reorder=only_reorder)
