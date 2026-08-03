import os
import requests
from typing import Optional, Dict, Any, List
from app.core.config import Config
from app.core.logger import app_logger

class ConnectorClient:
    """
    Dedicated HTTP Client managing communication between Pioneer Flow Billing ERP
    and Pioneer Connector microservice REST API.
    Centralizes connection management, timeouts, retries, authentication, and error handling.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 3.0, max_retries: int = 2):
        self.base_url = (base_url or os.environ.get("CONNECTOR_API_URL") or "http://localhost:8000").rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        # Pre-configure headers (and token auth if configured)
        self.session.headers.update({
            "User-Agent": "PioneerFlowBilling-ERP/2.0",
            "Accept": "application/json"
        })

    def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        Executes HTTP request with centralized error handling and retry logic.
        Returns parsed JSON object or None if unreachable.
        """
        url = f"{self.base_url}{endpoint}"
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=self.timeout
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    app_logger.warning(
                        f"[ConnectorClient] HTTP {response.status_code} from {url} (Attempt {attempt}/{self.max_retries})"
                    )
            except Exception as e:
                app_logger.warning(
                    f"[ConnectorClient] Network error reaching {url} (Attempt {attempt}/{self.max_retries}): {e}"
                )
        return None

    def get_health(self) -> Optional[Dict[str, Any]]:
        """Fetch connector and Tally connection health status."""
        return self._request("GET", "/health")

    def get_company(self) -> Optional[Dict[str, Any]]:
        """Fetch active Tally company metadata."""
        return self._request("GET", "/company")

    def get_stock(self) -> Optional[Dict[str, Any]]:
        """Fetch all canonical stock items."""
        return self._request("GET", "/stock")

    def get_stock_groups(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch stock groups."""
        return self._request("GET", "/stock/groups")

    def get_customers(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch customer directory ledgers."""
        return self._request("GET", "/customers")

    def get_ledgers(self) -> Optional[Dict[str, Any]]:
        """Fetch all ledgers (customers, suppliers, expenses, income, tax)."""
        return self._request("GET", "/ledgers")

    def get_inventory(self) -> Optional[Dict[str, Any]]:
        """Fetch inventory stock items (re-uses stock API)."""
        return self.get_stock()

    def get_sync_status(self) -> Optional[Dict[str, Any]]:
        """Fetch synchronization engine status and manifest."""
        return self._request("GET", "/sync/status")
