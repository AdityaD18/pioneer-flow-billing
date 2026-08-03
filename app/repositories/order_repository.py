from app.repositories.base_repository import BaseRepository
from app.core.config import Config

class OrderRepository(BaseRepository):
    """Centralized repository for ORDERS, ORDER_ITEMS, and APP_SETTINGS tables access."""

    @classmethod
    def get_settings(cls):
        rows = cls.query("SELECT key, value FROM APP_SETTINGS")
        return {r['key']: r['value'] for r in rows}

    @classmethod
    def get_gst_rate(cls):
        settings = cls.get_settings()
        try:
            return float(settings.get('gst_rate', Config.DEFAULT_GST_RATE))
        except ValueError:
            return Config.DEFAULT_GST_RATE

    @classmethod
    def update_setting(cls, key, value):
        cls.execute(
            "INSERT INTO APP_SETTINGS (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value))
        )

    @classmethod
    def get_by_id(cls, order_id):
        order = cls.query("SELECT * FROM ORDERS WHERE id = ?", (order_id,), one=True)
        if not order:
            return None
        items = cls.query("SELECT * FROM ORDER_ITEMS WHERE order_id = ?", (order_id,))
        result = dict(order)
        result['items'] = [dict(i) for i in items]
        return result
