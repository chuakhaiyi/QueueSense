# QueueSense

QueueSense is a campus queue-time prediction system. Record observations, compare a location/hour baseline with a Random Forest model, query predictions through FastAPI, and inspect them in Streamlit.

## Run locally

```bash
python -m venv .venv
pip install -r requirements.txt
uvicorn app.api:app --reload
streamlit run app/dashboard.py
```

API docs: `http://localhost:8000/docs` · Dashboard: `http://localhost:8501`

Useful API routes: `GET /health`, `POST /observations`, `GET /observations`, `GET /locations`, `POST /predict`, and `GET /evaluation`.

Set `QUEUESENSE_DB` to use a different SQLite file. The dashboard and API share the same database.

The model falls back to the baseline until enough observations exist. Accuracy is reported as MAE from the data you collect; no accuracy claim is made before measurement.

## Docker

```bash
docker build -t queuesense .
docker run --rm -p 8000:8000 -p 8501:8501 queuesense
```
