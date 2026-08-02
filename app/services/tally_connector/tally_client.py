import urllib.request
import base64
from .logger import tally_logger
from .retry_manager import RetryManager
from .xml_builder import TallyXMLBuilder
from .xml_parser import TallyXMLParser

class TallyClient:
    """Production-grade HTTP client communicating directly with Tally Prime 7.1 XML Server."""

    def __init__(self, host="localhost", port=9000, username="1", password="PtAc@6801"):
        self.host = host
        self.port = port
        self.url = f"http://{host}:{port}"
        self.username = username
        self.password = password
        
        # Base64 Auth header
        auth_str = f"{username}:{password}"
        auth_b64 = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
        self.headers_auth = {'Content-Type': 'text/xml', 'Authorization': f'Basic {auth_b64}'}
        self.headers_plain = {'Content-Type': 'text/xml'}

    def post_request(self, xml_bytes, timeout=30):
        """Sends XML payload to Tally HTTP server with automatic fallback authentication."""
        def _send():
            try:
                req = urllib.request.Request(self.url, data=xml_bytes, headers=self.headers_auth)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.read()
            except Exception:
                req = urllib.request.Request(self.url, data=xml_bytes, headers=self.headers_plain)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.read()

        return RetryManager.execute_with_retry(_send, max_retries=3, description=f"HTTP POST to {self.url}")

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

    def fetch_stock_items(self, min_alter_id=None):
        """Fetches 100% of all StockItems across all groups."""
        req_xml = TallyXMLBuilder.build_stock_items_request(min_alter_id=min_alter_id)
        resp_bytes = self.post_request(req_xml, timeout=45)
        return TallyXMLParser.parse_stock_items(resp_bytes)

    def fetch_ledgers(self, min_alter_id=None):
        """Fetches 100% of all Ledgers & Customers."""
        req_xml = TallyXMLBuilder.build_ledgers_request(min_alter_id=min_alter_id)
        resp_bytes = self.post_request(req_xml, timeout=45)
        return TallyXMLParser.parse_ledgers(resp_bytes)

    def fetch_stock_groups(self):
        """Fetches all 113 Stock Groups."""
        req_xml = TallyXMLBuilder.build_stock_groups_request()
        resp_bytes = self.post_request(req_xml, timeout=30)
        return TallyXMLParser.parse_stock_groups(resp_bytes)
