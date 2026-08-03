from fastapi.testclient import TestClient
from main import app
from tally.connection import TallyConnectionManager

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Pioneer Tally Connector"
    assert data["status"] == "running"

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "tally_health" in data
    health = data["tally_health"]
    assert "connected" in health
    assert "response_time_ms" in health
    assert "last_checked" in health

def test_connection_manager_mock_parse():
    xml_sample = """<ENVELOPE><BODY><DATA><COMPANYNAME>PIONEER AUTOMATION</COMPANYNAME><VERSION>7.1</VERSION></DATA></BODY></ENVELOPE>"""
    company, version = TallyConnectionManager._parse_company_response(xml_sample)
    assert company == "PIONEER AUTOMATION"
    assert version == "TallyPrime 7.1"
