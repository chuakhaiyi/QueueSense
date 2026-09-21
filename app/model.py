from datetime import datetime
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error


def _features(location, timestamp, queue_length=0, service_rate=1.0):
    dt = timestamp if isinstance(timestamp, datetime) else datetime.fromisoformat(timestamp)
    return [dt.hour, dt.weekday(), queue_length, service_rate]


class QueueModel:
    def __init__(self, observations):
        self.observations = list(observations)
        self.baseline = {}
        for row in self.observations:
            dt = datetime.fromisoformat(row["timestamp"])
            key = (row["location"], dt.hour)
            self.baseline.setdefault(key, []).append(float(row["wait_minutes"]))
        self.model = None
        if len(self.observations) >= 5:
            x = np.array([_features(r["location"], r["timestamp"], r["queue_length"], r["service_rate"]) for r in self.observations])
            y = np.array([float(r["wait_minutes"]) for r in self.observations])
            self.model = RandomForestRegressor(n_estimators=80, random_state=42, min_samples_leaf=2).fit(x, y)

    def predict(self, location, timestamp, queue_length=0, service_rate=1.0):
        dt = timestamp if isinstance(timestamp, datetime) else datetime.fromisoformat(timestamp)
        values = self.baseline.get((location, dt.hour), [])
        overall = [float(r["wait_minutes"]) for r in self.observations]
        baseline = float(np.mean(values or overall or [0]))
        prediction = float(self.model.predict([_features(location, dt, queue_length, service_rate)])[0]) if self.model else baseline
        samples = len(values)
        confidence = "high" if samples >= 20 else "medium" if samples >= 5 else "low"
        return {"location": location, "timestamp": dt.isoformat(), "prediction_minutes": round(max(0, prediction), 2), "baseline_minutes": round(max(0, baseline), 2), "confidence": confidence, "samples": samples}

    def mae(self):
        if not self.observations:
            return {"baseline_mae": None, "model_mae": None}
        y = np.array([float(r["wait_minutes"]) for r in self.observations])
        base = np.array([self.predict(r["location"], r["timestamp"], r["queue_length"], r["service_rate"])["baseline_minutes"] for r in self.observations])
        model = np.array([self.predict(r["location"], r["timestamp"], r["queue_length"], r["service_rate"])["prediction_minutes"] for r in self.observations])
        return {"baseline_mae": round(float(mean_absolute_error(y, base)), 2), "model_mae": round(float(mean_absolute_error(y, model)), 2)}

    def evaluate(self):
        if len(self.observations) < 5:
            return {"status": "insufficient_data", "required": 5, "samples": len(self.observations), **self.mae()}
        metrics = self.mae()
        return {"status": "ready", "samples": len(self.observations), **metrics, "improvement_minutes": round(metrics["baseline_mae"] - metrics["model_mae"], 2)}
