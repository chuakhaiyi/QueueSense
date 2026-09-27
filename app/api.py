import os
from contextlib import closing
from datetime import datetime, date
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app import service
from app.db import connect, locations as db_locations, recent_rows

app = FastAPI(title='QueueSense', version='1.0.0')
DB_PATH = None
origins = [v.strip() for v in os.getenv('QUEUESENSE_CORS', '').split(',') if v.strip()]
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])
Observation = service.Observation


class PredictionRequest(BaseModel):
    location: service.Name
    timestamp: datetime


@app.get('/health')
def health():
    with closing(connect(DB_PATH)) as conn:
        conn.execute('SELECT 1')
    return {'status': 'ok', 'service': 'queuesense'}


@app.post('/observations', status_code=201)
def create_observation(item: Observation):
    return {'id': service.save(item, DB_PATH)}


@app.get('/observations')
def observation_history(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    with closing(connect(DB_PATH)) as conn:
        return [dict(r) for r in recent_rows(conn, limit, offset)]


@app.get('/locations')
def locations():
    with closing(connect(DB_PATH)) as conn:
        return [r['name'] for r in db_locations(conn)]


@app.post('/predict')
def predict(item: PredictionRequest):
    model, metrics = service.current_model(DB_PATH)
    result = model.predict(item.location, service.campus_time(item.timestamp))
    if result['prediction_minutes'] is None:
        raise HTTPException(404, 'No training observations for this location. Collect data and retrain if needed.')
    return result


@app.get('/forecast')
def forecast(location: str, day: date):
    return service.forecast(location, day, DB_PATH)


@app.get('/metrics')
@app.get('/evaluation')
def evaluation():
    return service.current_model(DB_PATH)[1]


@app.post('/train')
def train():
    try:
        return service.train(DB_PATH)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@app.get('/export')
def export():
    return Response(service.export_csv(DB_PATH), media_type='text/csv', headers={'Content-Disposition': 'attachment; filename=queuesense.csv'})


@app.post('/import')
def import_csv(content: str = Body(media_type='text/csv', max_length=2_000_000)):
    try:
        return {'imported': service.import_csv(content, DB_PATH)}
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
