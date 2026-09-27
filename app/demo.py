"""Deterministic, clearly synthetic observations for the isolated demo workspace."""
import argparse
import random
from contextlib import closing
from datetime import timedelta
from app import service
from app.db import connect, add_observation

LOCATIONS = ['North Hall Cafeteria', 'Library Coffee Bar', 'Student Services', 'Campus Clinic']


def seed(path):
    if service.dataset(path):
        return
    rng = random.Random(42)
    today = service.campus_now().replace(hour=0, minute=0, second=0, microsecond=0)
    with closing(connect(path)) as conn, conn:
        for days in range(28, 0, -1):
            for hour in range(8, 19):
                for index, name in enumerate(LOCATIONS):
                    stamp = today - timedelta(days=days) + timedelta(hours=hour)
                    peak = max(0, 1 - abs(hour - (12 if index < 2 else 10))/3)
                    wait = round(max(0, 3 + index*2 + peak*(16-index*2) + rng.gauss(0, 2)), 1)
                    rate = [1.8, 1.2, .5, .25][index]
                    add_observation(conn, name, stamp.isoformat(), round(wait*rate), rate, wait, commit=False)
    service.train(path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create isolated synthetic demo data')
    parser.add_argument('--path', default='data/demo.db')
    seed(parser.parse_args().path)
