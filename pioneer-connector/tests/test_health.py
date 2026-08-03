from fastapi.testclient import TestClient
from main import app

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
    assert data["status"] == "healthy"
    assert "tally_target" in data

def test_sync_trigger_endpoint():
    response = client.post("/api/v1/sync/trigger")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "initiated"
