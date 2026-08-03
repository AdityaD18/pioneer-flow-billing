import time
from datetime import datetime
import requests
import xml.etree.ElementTree as ET
from config.settings import settings

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
    def test_connection(cls, host: str = None, port: int = None, timeout: int = None) -> dict:
        """
        Probes TallyPrime XML HTTP interface on host:port.
        Returns detailed health diagnostic report dictionary.
        """
        target_host = host or settings.TALLY_HOST
        target_port = port or settings.TALLY_PORT
        conn_timeout = timeout or settings.TALLY_TIMEOUT
        
        url = f"http://{target_host}:{target_port}"
        start_time = time.perf_counter()
        last_checked = datetime.utcnow().isoformat() + "Z"
        
        try:
            response = requests.post(
                url,
                data=cls.COMPANY_LIST_XML,
                headers={"Content-Type": "text/xml"},
                timeout=conn_timeout
            )
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            
            if response.status_code == 200:
                company_name, tally_version = cls._parse_company_response(response.text)
                return {
                    "connected": True,
                    "company_name": company_name or settings.TALLY_COMPANY,
                    "tally_version": tally_version or "TallyPrime 7.1",
                    "response_time_ms": elapsed_ms,
                    "last_checked": last_checked,
                    "endpoint": url,
                    "error_message": None
                }
            else:
                return {
                    "connected": False,
                    "company_name": None,
                    "tally_version": None,
                    "response_time_ms": elapsed_ms,
                    "last_checked": last_checked,
                    "endpoint": url,
                    "error_message": f"HTTP Status {response.status_code}: {response.reason}"
                }
                
        except requests.exceptions.ConnectionError:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "connected": False,
                "company_name": None,
                "tally_version": None,
                "response_time_ms": elapsed_ms,
                "last_checked": last_checked,
                "endpoint": url,
                "error_message": f"Connection refused at {url}. Ensure TallyPrime is running and XML ODBC port is enabled."
            }
        except requests.exceptions.Timeout:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "connected": False,
                "company_name": None,
                "tally_version": None,
                "response_time_ms": elapsed_ms,
                "last_checked": last_checked,
                "endpoint": url,
                "error_message": f"Connection timed out after {conn_timeout}s at {url}."
            }
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "connected": False,
                "company_name": None,
                "tally_version": None,
                "response_time_ms": elapsed_ms,
                "last_checked": last_checked,
                "endpoint": url,
                "error_message": str(e)
            }

    @staticmethod
    def _parse_company_response(xml_text: str):
        """Parses active company name and version from Tally XML response."""
        company_name = None
        tally_version = "TallyPrime 7.1"
        
        try:
            root = ET.fromstring(xml_text)
            # Search for company name tags
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
