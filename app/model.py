"""Time-only forecasts: future queue lengths are not known at prediction time."""
from datetime import datetime
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_extraction import DictVectorizer
from sklearn.pipeline import make_pipeline
from sklearn.metrics import mean_absolute_error


def features(location, timestamp):
    dt = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp
    return {'location': location, 'hour': dt.hour, 'weekday': dt.weekday()}


class QueueModel:
    def __init__(self, observations):
        self.observations = sorted([dict(r) for r in observations], key=lambda r: r['timestamp'])
        self.model = None
        if len(self.observations) >= 30:
            self.model = make_pipeline(DictVectorizer(sparse=False), RandomForestRegressor(
                n_estimators=80, min_samples_leaf=3, random_state=42, n_jobs=1))
            self.model.fit([features(r['location'], r['timestamp']) for r in self.observations],
                           [r['wait_minutes'] for r in self.observations])

    def predict(self, location, timestamp, queue_length=None, service_rate=None):
        dt = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp
        local = [r for r in self.observations if r['location'] == location]
        hourly = [r for r in local if datetime.fromisoformat(r['timestamp']).hour == dt.hour]
        values = [r['wait_minutes'] for r in (hourly or local)]
        baseline = float(np.mean(values)) if values else None
        estimate = float(self.model.predict([features(location, dt)])[0]) if self.model and local else baseline
        return {'location': location, 'timestamp': dt.isoformat(),
                'prediction_minutes': round(max(0, estimate), 1) if estimate is not None else None,
                'baseline_minutes': round(baseline, 1) if baseline is not None else None,
                'method': 'random_forest' if self.model and local else 'baseline',
                'confidence': 'medium' if len(hourly) >= 10 else 'low',
                'samples': len(hourly), 'location_samples': len(local),
                'explanation': 'Data support only, not a calibrated probability. Hourly mean falls back to this location mean.'}

    def evaluate(self):
        result = {'status': 'insufficient_data', 'samples': len(self.observations), 'required': 50,
                  'baseline_mae': None, 'model_mae': None,
                  'evaluation': 'Chronological holdout: newest 20% of timestamps, never training rows.'}
        if len(self.observations) < 50:
            return result
        boundary = self.observations[int(len(self.observations) * .8)]['timestamp']
        train = [r for r in self.observations if r['timestamp'] < boundary]
        test = [r for r in self.observations if r['timestamp'] >= boundary]
        if len(train) < 30 or len(test) < 10:
            return result
        fitted = QueueModel(train)
        predictions = [(r, fitted.predict(r['location'], r['timestamp'])) for r in test]
        supported = [(r, p) for r, p in predictions if p['prediction_minutes'] is not None]
        if len(supported) < 10:
            return result
        truth = [r['wait_minutes'] for r, p in supported]
        result.update(status='evaluated', train_samples=len(train), test_samples=len(supported),
                      skipped_unseen_locations=len(test)-len(supported), cutoff=boundary,
                      baseline_mae=round(mean_absolute_error(truth, [p['baseline_minutes'] for r, p in supported]), 2),
                      model_mae=round(mean_absolute_error(truth, [p['prediction_minutes'] for r, p in supported]), 2))
        return result

    def mae(self):
        return self.evaluate()
