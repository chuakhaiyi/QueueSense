from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from app import api, service
from app.model import QueueModel


def observation(**changes):
    return dict(location='Cafe', timestamp='2026-01-01T12:00:00', queue_length=3, service_rate=1, wait_minutes=8, **changes)


def test_capture_transfer_and_training(tmp_path, monkeypatch):
    path = str(tmp_path / 'test.db')
    monkeypatch.setattr(api, 'DB_PATH', path)
    client = TestClient(api.app)
    assert client.post('/train').status_code == 422
    assert client.post('/observations', json=observation()).status_code == 201
    for key, bad in [('location','  '), ('service_rate',0), ('queue_length',-1), ('timestamp','2099-01-01T12:00:00')]:
        payload = observation()
        payload[key] = bad
        assert client.post('/observations', json=payload).status_code == 422
    assert client.post('/predict', json={'location':'Unknown','timestamp':'2026-01-01T12:00:00'}).status_code == 404
    assert client.get('/observations?limit=0').status_code == 422
    text = client.get('/export').text
    bad = text + 'Bad,invalid,2,1,3\n'
    assert client.post('/import', content=bad, headers={'Content-Type':'text/csv'}).status_code == 422
    assert len(service.dataset(path)) == 1  # invalid batch did not partially commit
    assert client.post('/import', content=text, headers={'Content-Type':'text/csv'}).json()['imported'] == 1
    for i in range(60):
        payload = observation()
        payload['timestamp'] = (datetime(2026,1,2,12)+timedelta(days=i)).isoformat()
        payload['wait_minutes'] = 8 + i % 3
        service.save(service.Observation(**payload), path)
    result = client.post('/train')
    assert result.status_code == 200
    assert result.json()['status'] == 'evaluated'
    service.fitted.cache_clear()
    assert client.get('/evaluation').json()['trained_at'] == result.json()['trained_at']
    assert client.post('/predict',json={'location':'Cafe','timestamp':'2026-04-01T12:00:00'}).json()['method'] == 'random_forest'
    assert len(client.get('/forecast?location=Cafe&day=2026-04-01').json()) == 11


def test_temporal_holdout_has_no_future_leakage():
    data = [dict(location='Cafe', timestamp=(datetime(2026,1,1)+timedelta(days=i)).isoformat(), queue_length=1, service_rate=1, wait_minutes=0 if i<80 else 100) for i in range(100)]
    result = QueueModel(data).evaluate()
    assert result['baseline_mae'] == 100
    assert result['model_mae'] == 100
    assert result['train_samples'] == 80
    assert result['test_samples'] == 20


def test_location_is_a_model_feature():
    data = [dict(location=name, timestamp=f'2026-01-{day:02d}T12:00:00', queue_length=1, service_rate=1, wait_minutes=wait)
            for day in range(1,29) for name,wait in [('Cafe',2),('Clinic',40)]]
    model = QueueModel(data)
    assert model.predict('Cafe', datetime(2026,2,1,12))['prediction_minutes'] < 5
    assert model.predict('Clinic', datetime(2026,2,1,12))['prediction_minutes'] > 35
    assert model.predict('Unknown', datetime(2026,2,1,12))['prediction_minutes'] is None
