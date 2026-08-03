import time
import logging
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
import requests
import xml.etree.ElementTree as ET
from config.settings import settings

logger = logging.getLogger("pioneer_connector.tally")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

class TallyConnectionManager:
    """Connection manager for probing, diagnosing, and reporting TallyPrime instance status."""

    COMPANY_LIST_XML = """<ENVELOPE>
<HEADER>
<TALLYREQUEST>Export Data</TALLYREQUEST>
</HEADER>
<BODY>
<EXPORTDATA>
<REQUESTDESC>
<REPORTNAME>List of Companies</REPORTNAME>
<STATICVARIABLES>
<SVEXPORTFORMAT>$$SYSNAME:XML</SVEXPORTFORMAT>
</STATICVARIABLES>
</REQUESTDESC>
</EXPORTDATA>
</BODY>
</ENVELOPE>"""

    @classmethod
    def get_candidate_urls(cls, host: Optional[str] = None, port: Optional[int] = None) -> list:
        """Returns ordered list of candidate endpoints (IPv4 127.0.0.1 first to prevent IPv6 ::1 refusal)."""
        target_port = port or settings.TALLY_PORT
        target_host = host or settings.TALLY_HOST

        candidates = [
            f"http://127.0.0.1:{target_port}",
            f"http://localhost:{target_port}"
        ]
        if target_host not in ("127.0.0.1", "localhost"):
            candidates.insert(0, f"http://{target_host}:{target_port}")

        # Deduplicate while preserving order
        seen = set()
        ordered = []
        for url in candidates:
            if url not in seen:
                seen.add(url)
                ordered.append(url)
        return ordered

    @classmethod
    def test_connection(cls, host: str = None, port: int = None, timeout: int = None) -> dict:
        """
        Probes TallyPrime HTTP interface.
        Performs a lightweight GET request first to verify Tally reachability without requiring XML.
        Tries both 127.0.0.1 and localhost to resolve IPv4/IPv6 differences.
        """
        conn_timeout = timeout or settings.TALLY_TIMEOUT
        candidate_urls = cls.get_candidate_urls(host, port)
        
        last_checked = datetime.utcnow().isoformat() + "Z"
        start_time = time.perf_counter()

        connected_url = None
        get_response_text = ""
        last_exception_info = ""

        # Step 1: Lightweight HTTP GET Reachability Probe
        for url in candidate_urls:
            req_headers = {"User-Agent": "PioneerTallyConnector/1.0", "Accept": "*/*"}
            logger.info(f"[TallyProbe] Executing GET probe -> URL: {url} | Method: GET | Headers: {req_headers} | Timeout: {conn_timeout}s")
            
            try:
                get_start = time.perf_counter()
                resp = requests.get(url, headers=req_headers, timeout=conn_timeout)
                get_elapsed = round((time.perf_counter() - get_start) * 1000, 2)
                
                logger.info(f"[TallyProbe] GET Response <- URL: {url} | Status Code: {resp.status_code} | Latency: {get_elapsed}ms | Content Snippet: {resp.text[:100]!r}")

                # Tally HTTP server returns 200 OK with '<RESPONSE>TallyPrime Server is Running</RESPONSE>'
                if resp.status_code == 200 or "<RESPONSE>" in resp.text or "Tally" in resp.text:
                    connected_url = url
                    get_response_text = resp.text
                    break
                else:
                    logger.warning(f"[TallyProbe] Unexpected HTTP Status {resp.status_code} from {url}")
            except Exception as e:
                exc_type = type(e).__name__
                exc_msg = str(e)
                last_exception_info = f"URL: {url} | Exception: {exc_type} ({exc_msg})"
                logger.warning(f"[TallyProbe] GET Failed -> {last_exception_info}")

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if not connected_url:
            logger.error(f"[TallyProbe] All connection attempts failed. Candidates: {candidate_urls} | Last Error: {last_exception_info}")
            return {
                "connected": False,
                "company_name": None,
                "tally_version": None,
                "response_time_ms": elapsed_ms,
                "last_checked": last_checked,
                "endpoint": candidate_urls[0],
                "error_message": f"Connection refused across candidates {candidate_urls}. Details: {last_exception_info}"
            }

        # Step 2: Connection Confirmed! Attempt Optional XML Company Metadata Retrieval via POST
        company_name = settings.TALLY_COMPANY
        tally_version = "TallyPrime 7.1"

        post_headers = {"Content-Type": "text/xml", "User-Agent": "PioneerTallyConnector/1.0"}
        logger.info(f"[TallyProbe] Executing Company Metadata XML POST -> URL: {connected_url} | Method: POST | Headers: {post_headers}")

        try:
            post_resp = requests.post(connected_url, data=cls.COMPANY_LIST_XML, headers=post_headers, timeout=conn_timeout)
            logger.info(f"[TallyProbe] POST Response <- URL: {connected_url} | Status Code: {post_resp.status_code} | Snippet: {post_resp.text[:100]!r}")
            
            if post_resp.status_code == 200:
                parsed_company, parsed_version = cls._parse_company_response(post_resp.text)
                if parsed_company:
                    company_name = parsed_company
                if parsed_version:
                    tally_version = parsed_version
        except Exception as e:
            logger.warning(f"[TallyProbe] Company XML POST failed ({type(e).__name__}: {e}). Using default company metadata.")

        return {
            "connected": True,
            "company_name": company_name,
            "tally_version": tally_version,
            "response_time_ms": elapsed_ms,
            "last_checked": last_checked,
            "endpoint": connected_url,
            "error_message": None
        }

    @staticmethod
    def _parse_company_response(xml_text: str) -> Tuple[Optional[str], str]:
        """Parses active company name and version from Tally XML response."""
        company_name = None
        tally_version = "TallyPrime 7.1"
        
        try:
            root = ET.fromstring(xml_text)
            for elem in root.iter():
                tag_lower = elem.tag.lower()
                if "company" in tag_lower or "name" in tag_lower:
                    if elem.text and elem.text.strip():
                        company_name = elem.text.strip()
                        break
                if "version" in tag_lower or "build" in tag_lower:
                    if elem.text and elem.text.strip():
                        tally_version = f"TallyPrime {elem.text.strip()}"
        except Exception:
            pass
            
        return company_name, tally_version
