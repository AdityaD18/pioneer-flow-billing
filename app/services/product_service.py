from app.repositories.product_repository import ProductRepository
from app.core.logger import app_logger

class ProductService:
    """Service handling catalog product queries and price modifications."""

    @classmethod
    def get_distinct_series(cls):
        """Retrieves distinct product series options."""
        return ProductRepository.get_distinct_series()

    @classmethod
    def get_catalog_products(cls, search_kw=None, series=None):
        """Retrieves catalog products."""
        return ProductRepository.get_catalog(search_kw=search_kw, series=series)

    @classmethod
    def get_all_billing_products(cls):
        """Retrieves lightweight product list for billing line items."""
        return ProductRepository.get_all_billing_products()

    @classmethod
    def update_product_cost_price(cls, product_id, price_per_100_pcs):
        """Updates cost price for a product."""
        app_logger.info(f"Updating cost price for product ID {product_id} to INR {price_per_100_pcs} / 100pcs.")
        ProductRepository.update_cost_price(product_id, price_per_100_pcs)
