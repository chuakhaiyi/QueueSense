"""Validation, CSV transfer and explicit model lifecycle shared by API and UI."""
import csv
import io
import json
from contextlib import closing
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from typing import Annotated
from pydantic import BaseModel, Field, ConfigDict, StringConstraints, field_validator
from app.db import connect, rows, add_observation
from app.model import QueueModel

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
CAMPUS_TZ = timezone(timedelta(hours=8))


def campus_now():
    return datetime.now(CAMPUS_TZ).replace(tzinfo=None)


def campus_time(value):
    return value.astimezone(CAMPUS_TZ).replace(tzinfo=None) if value.tzinfo else value


class Observation(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    location: Name
    timestamp: datetime
    queue_length: int = Field(ge=0, le=10000)
    service_rate: float = Field(gt=0, le=10000)
    wait_minutes: float = Field(ge=0, le=1440)

    @field_validator('timestamp')
    @classmethod
    def valid_time(cls, value):
        value = campus_time(value)
        if value > campus_now() + timedelta(minutes=5):
            raise ValueError('Observation time cannot be in the future')
        return value


def save(item, path=None):
    with closing(connect(path)) as conn:
        return add_observation(conn, item.location, item.timestamp.isoformat(), item.queue_length, item.service_rate, item.wait_minutes)


def dataset(path=None):
    with closing(connect(path)) as conn:
        return [dict(r) for r in rows(conn)]


@lru_cache(maxsize=8)
def fitted(snapshot):
    return QueueModel(json.loads(snapshot))


def current_model(path=None):
    with closing(connect(path)) as conn:
        run = conn.execute('SELECT * FROM model_runs ORDER BY id DESC LIMIT 1').fetchone()
    if run:
        return fitted(run['dataset']), {**json.loads(run['metrics']), 'trained_at': run['trained_at']}
    model = QueueModel([])
    model.observations = dataset(path)
    return model, {'status': 'not_trained', 'baseline_mae': None, 'model_mae': None}


def train(path=None):
    data = dataset(path)
    if len(data) < 30:
        raise ValueError('Collect at least 30 observations before training.')
    snapshot = json.dumps(data)
    model = fitted(snapshot)
    metrics = model.evaluate()
    stamp = datetime.now(timezone.utc).isoformat()
    with closing(connect(path)) as conn:
        conn.execute('INSERT INTO model_runs(trained_at,dataset,metrics) VALUES (?,?,?)', (stamp, snapshot, json.dumps(metrics)))
        conn.commit()
    return {**metrics, 'trained_at': stamp}


def export_csv(path=None):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(Observation.model_fields), extrasaction='ignore')
    writer.writeheader()
    writer.writerows(dataset(path))
    return output.getvalue()


def import_csv(text, path=None):
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    if not set(Observation.model_fields).issubset(reader.fieldnames or []):
        raise ValueError('CSV needs location, timestamp, queue_length, service_rate, wait_minutes headers.')
    items = []
    for line, row in enumerate(reader, 2):
        if len(items) >= 10000:
            raise ValueError('Import at most 10,000 rows at a time.')
        try:
            items.append(Observation.model_validate(row))
        except ValueError as error:
            raise ValueError(f'CSV row {line}: {error}') from error
    with closing(connect(path)) as conn, conn:
        for item in items:
            add_observation(conn, item.location, item.timestamp.isoformat(), item.queue_length, item.service_rate, item.wait_minutes, commit=False)
    return len(items)


def forecast(location, day, path=None):
    model, _ = current_model(path)
    return [model.predict(location, datetime.combine(day, datetime.min.time()).replace(hour=h)) for h in range(8, 19)]
