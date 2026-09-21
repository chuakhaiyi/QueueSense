from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .db import connect, add_observation, rows, locations as db_locations, recent_rows
from .model import QueueModel

app = FastAPI(title="QueueSense API")
DB_PATH = "queuesense.db"


class Observation(BaseModel):
    location: str = Field(min_length=1)
    timestamp: datetime
    queue_length: int = Field(ge=0)
    service_rate: float = Field(gt=0)
    wait_minutes: float = Field(ge=0)


class PredictionRequest(BaseModel):
    location: str = Field(min_length=1)
    timestamp: datetime
    queue_length: int = Field(default=0, ge=0)
    service_rate: float = Field(default=1, gt=0)


@app.get("/health")
def health():
    return {"status": "ok", "service": "queuesense"}


@app.post("/observations", status_code=201)
def create_observation(item: Observation):
    conn = connect(DB_PATH)
    return {"id": add_observation(conn, item.location, item.timestamp.isoformat(), item.queue_length, item.service_rate, item.wait_minutes)}


@app.get("/locations")
def locations():
    conn = connect(DB_PATH)
    return [r["name"] for r in db_locations(conn)]


@app.get("/observations")
def observation_history(limit: int = 100, offset: int = 0):
    if not 1 <= limit <= 500 or offset < 0:
        raise HTTPException(422, "limit must be 1-500 and offset must be non-negative")
    return [dict(r) for r in recent_rows(connect(DB_PATH), limit, offset)]


@app.post("/predict")
def predict(item: PredictionRequest):
    conn = connect(DB_PATH)
    data = rows(conn)
    if not data:
        raise HTTPException(400, "Add at least one observation before predicting")
    return QueueModel(data).predict(item.location, item.timestamp, item.queue_length, item.service_rate)


@app.get("/metrics")
def metrics():
    return QueueModel(rows(connect(DB_PATH))).mae()


@app.get("/evaluation")
def evaluation():
    return QueueModel(rows(connect(DB_PATH))).evaluate()
