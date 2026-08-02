import urllib.request
import base64
from .config import tally_config
from .logger import tally_logger
from .retry_manager import RetryManager
from .xml_builder import TallyXMLBuilder
from .xml_parser import TallyXMLParser

class TallyClient:
    """Production-grade HTTP client communicating directly with Tally Prime 7.1 XML Server."""

    def __init__(self, host=None, port=None, username=None, password=None):
        self.host = host or tally_config.get("host", "localhost")
        self.port = port or tally_config.get("port", 9000)
        self.url = f"http://{self.host}:{self.port}"
        self.username = username or tally_config.get("username", "1")
        self.password = password or tally_config.get("password", "PtAc@6801")
        self.timeout = tally_config.get("timeout_seconds", 45)
        self.max_retries = tally_config.get("max_retries", 3)
        
        auth_str = f"{self.username}:{self.password}"
        auth_b64 = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
        self.headers_auth = {'Content-Type': 'text/xml', 'Authorization': f'Basic {auth_b64}'}
        self.headers_plain = {'Content-Type': 'text/xml'}

    def post_request(self, xml_bytes, timeout=None):
        """Sends XML payload to Tally HTTP server with automatic fallback authentication."""
        t_out = timeout or self.timeout
        
        def _send():
            try:
                req = urllib.request.Request(self.url, data=xml_bytes, headers=self.headers_auth)
                with urllib.request.urlopen(req, timeout=t_out) as resp:
                    return resp.read()
            except Exception:
                req = urllib.request.Request(self.url, data=xml_bytes, headers=self.headers_plain)
                with urllib.request.urlopen(req, timeout=t_out) as resp:
                    return resp.read()

        return RetryManager.execute_with_retry(_send, max_retries=self.max_retries, description=f"HTTP POST to {self.url}")

    def is_connected(self):
        """Verifies if Tally Prime is active and responding on HTTP port."""
        try:
            req_xml = TallyXMLBuilder.build_active_company_request()
            resp_bytes = self.post_request(req_xml, timeout=5)
            return resp_bytes is not None and len(resp_bytes) > 0
        except Exception as ex:
            tally_logger.debug(f"Tally connection health check failed: {ex}")
            return False

    def get_active_company(self):
        """Returns the active Tally Prime company name."""
        try:
            req_xml = TallyXMLBuilder.build_active_company_request()
            resp_bytes = self.post_request(req_xml, timeout=10)
            return TallyXMLParser.parse_active_company(resp_bytes)
        except Exception as ex:
            tally_logger.warning(f"Could not retrieve active company name: {ex}")
            return "Pioneer Technology (Default)"

    def get_object_count(self, object_type):
        """Dynamically queries Tally for the exact expected count of any object type."""
        try:
            req_xml = TallyXMLBuilder.build_object_count_request(object_type)
            resp_bytes = self.post_request(req_xml, timeout=20)
            return TallyXMLParser.parse_object_count(resp_bytes, object_tag=object_type)
        except Exception as ex:
            tally_logger.warning(f"Failed to query dynamic Tally object count for [{object_type}]: {ex}")
            return 0

    def fetch_stock_items(self, min_alter_id=None):
        """Fetches 100% of all StockItems across all groups."""
        req_xml = TallyXMLBuilder.build_stock_items_request(min_alter_id=min_alter_id)
        resp_bytes = self.post_request(req_xml, timeout=60)
        return TallyXMLParser.parse_stock_items(resp_bytes)

    def fetch_ledgers(self, min_alter_id=None):
        """Fetches 100% of all Ledgers & Customers."""
        req_xml = TallyXMLBuilder.build_ledgers_request(min_alter_id=min_alter_id)
        resp_bytes = self.post_request(req_xml, timeout=60)
        return TallyXMLParser.parse_ledgers(resp_bytes)

    def fetch_stock_groups(self):
        """Fetches all Stock Groups."""
        req_xml = TallyXMLBuilder.build_stock_groups_request()
        resp_bytes = self.post_request(req_xml, timeout=30)
        return TallyXMLParser.parse_stock_groups(resp_bytes)
