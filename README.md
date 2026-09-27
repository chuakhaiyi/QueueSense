# QueueSense

**A little less waiting. More campus.**

A complete local campus queue research application: collect measured waits, compare locations and visit times, explore hourly trends, and compare a Random Forest against a location/hour baseline. Built with Python, FastAPI, SQLite, Pandas, scikit-learn and Streamlit.

## Run

Requires Python 3.11. From the project folder:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app/dashboard.py
```

Open http://localhost:8501. In a second terminal using the same environment:

```powershell
python -m uvicorn app.api:app --host 127.0.0.1 --port 8000
```

API documentation: http://localhost:8000/docs. On macOS/Linux activate the environment with `source .venv/bin/activate`.

## What you can do

- **Overview:** estimated waits, observation freshness, sample support and daily forecasts.
- **Plan a visit:** select appropriate locations for your errand and compare future hourly estimates. Planning hours are 08:00–18:00; verify actual opening hours independently.
- **Record observations:** capture location, timestamp, queue length, service rate and measured wait, with shared API/UI validation.
- **Data & insights:** filter history, view measured hourly averages, export CSV and atomically import validated CSV batches.
- **Model studio:** explicitly train/retrain, persist reproducible snapshots and inspect chronological held-out MAE.
- **Demo workspace:** an opt-in, deterministic synthetic campus dataset in a separate database. Demo metrics are not evidence of real-world accuracy.

The dashboard and API use the same service layer and SQLite data. You can use the dashboard without starting the API.

## Data and model behavior

All timestamps use campus time UTC+08:00. Offset-aware input is converted; naive input is interpreted as campus time. Record actual measured waits, not predictions. Queue length counts people waiting; service rate is people served per minute.

Before training, forecasts use the average wait for that location/hour, falling back to that location's overall average. Unknown locations return no estimate rather than an invented zero. After training, forecasts use a Random Forest with location, hour and weekday. Future queue length and service rate are deliberately excluded because they are unknown at planning time.

Training requires 30 observations. Evaluation requires at least 50 observations, at least 30 earlier training rows and 10 test rows for known locations. The newest 20% of timestamps are held out, including all rows at the split timestamp. Both methods learn only from earlier rows. The production predictor is then fitted to the full training snapshot. New observations require retraining. These thresholds are operational minimums, not proof of sufficient data or accuracy.

MAE is mean absolute error in minutes: lower is better. A model may perform worse than the baseline. Sample-support labels are **not calibrated confidence probabilities or intervals**. No accuracy is claimed until adequate real observations have been collected and evaluated. Queue conditions, holidays, term dates and opening hours can change.

Training snapshots and evaluation metadata are stored as JSON in SQLite; the estimator is reconstructed once per process and cached. This avoids loading executable serialized model files. It is suitable for a small campus pilot; large datasets need a separate model registry and background training.

## CSV

```csv
location,timestamp,queue_length,service_rate,wait_minutes
North Hall Cafeteria,2026-01-12T12:00:00,12,1.5,8
```

Imports append rows (re-importing creates duplicates), accept at most 10,000 rows and are all-or-nothing on validation errors. UI/API requests are limited to 2 MB. CSV exports contain all recorded observations.

## API

| Method | Route | Purpose |
|---|---|---|
| GET | `/health` | Database connectivity |
| POST | `/observations` | Validate and save an observation |
| GET | `/observations?limit=100&offset=0` | Paginated history |
| GET | `/locations` | Recorded locations |
| POST | `/predict` | Forecast for location and timestamp |
| GET | `/forecast?location=…&day=2026-10-01` | Hourly visit estimates |
| POST | `/train` | Train, evaluate and save snapshot |
| GET | `/evaluation` or `/metrics` | Last training metadata and holdout MAE |
| GET | `/export` | Download observations as CSV |
| POST | `/import` | CSV body with `Content-Type: text/csv` |

## Configuration and deployment

- `QUEUESENSE_DB`: database file, default `queuesense.db`. Use the same absolute path in both processes if their working directories differ.
- `QUEUESENSE_CORS`: optional comma-separated browser origins for the API. Empty by default.

```powershell
docker compose up --build
```

Compose starts separate API and dashboard processes with health checks, localhost-only published ports, and a shared persistent `queue-data` volume. `docker compose down` keeps observations; do not add `--volumes` unless you intend to delete them. Stop services before copying the SQLite file for backup.

**Deployment boundary:** this is a local/trusted-network application without authentication or role-based access. Do not expose it publicly without an authenticated gateway, TLS, request limits and a backup policy. It does not collect personal student information.

## Verify

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests cover input validation, API capture, CSV atomicity, persisted training, location-specific predictions, temporal leakage, dashboard pages and demo isolation.

## Portfolio description

Built a campus queue-time prediction system with a data collection pipeline, baseline comparison, REST API, and dashboard for estimating wait times by location and time of day.
