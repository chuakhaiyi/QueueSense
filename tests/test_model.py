from datetime import datetime
from app.model import QueueModel


def test_prediction_uses_location_hour_baseline():
    data = [{"location": "Cafe", "timestamp": "2026-01-01T12:00:00", "queue_length": 4, "service_rate": 1, "wait_minutes": 10}, {"location": "Cafe", "timestamp": "2026-01-08T12:00:00", "queue_length": 6, "service_rate": 1, "wait_minutes": 14}]
    result = QueueModel(data).predict("Cafe", datetime(2026, 1, 15, 12))
    assert result["baseline_minutes"] == 12
    assert result["confidence"] == "low"
