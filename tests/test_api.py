from fastapi.testclient import TestClient
from app import api


def test_health_and_prediction_validation(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DB_PATH", str(tmp_path / "test.db"))
    client = TestClient(api.app)
    assert client.get("/health").json()["status"] == "ok"
    assert client.post("/observations", json={"location": "Cafe", "timestamp": "2026-01-01T12:00:00", "queue_length": 3, "service_rate": 1, "wait_minutes": 8}).status_code == 201
    assert client.post("/predict", json={"location": "Cafe", "timestamp": "2026-01-01T12:30:00"}).status_code == 200
    assert client.post("/observations", json={"location": "Cafe", "timestamp": "2026-01-01T12:00:00", "queue_length": -1, "service_rate": 1, "wait_minutes": 8}).status_code == 422
