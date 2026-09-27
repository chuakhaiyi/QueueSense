import os
import sqlite3
from pathlib import Path

SCHEMA = '''
CREATE TABLE IF NOT EXISTS locations (name TEXT PRIMARY KEY, active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS observations (
 id INTEGER PRIMARY KEY AUTOINCREMENT, location TEXT NOT NULL,
 timestamp TEXT NOT NULL, queue_length INTEGER NOT NULL CHECK(queue_length >= 0),
 service_rate REAL NOT NULL CHECK(service_rate > 0), wait_minutes REAL NOT NULL CHECK(wait_minutes >= 0));
CREATE INDEX IF NOT EXISTS observation_time ON observations(timestamp);
CREATE TABLE IF NOT EXISTS model_runs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, trained_at TEXT NOT NULL,
 dataset TEXT NOT NULL, metrics TEXT NOT NULL);
'''


def connect(path=None):
    target = path or os.getenv('QUEUESENSE_DB', 'queuesense.db')
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.execute('INSERT OR IGNORE INTO locations(name) SELECT DISTINCT location FROM observations')
    conn.commit()
    return conn


def add_observation(conn, location, timestamp, queue_length, service_rate, wait_minutes, commit=True):
    conn.execute('INSERT OR IGNORE INTO locations(name) VALUES (?)', (location,))
    cur = conn.execute('INSERT INTO observations(location,timestamp,queue_length,service_rate,wait_minutes) VALUES (?,?,?,?,?)',
                       (location, timestamp, queue_length, service_rate, wait_minutes))
    if commit:
        conn.commit()
    return cur.lastrowid


def rows(conn):
    return conn.execute('SELECT * FROM observations ORDER BY timestamp,id').fetchall()


def locations(conn):
    return conn.execute('SELECT name FROM locations WHERE active=1 ORDER BY name').fetchall()


def recent_rows(conn, limit=100, offset=0):
    return conn.execute('SELECT * FROM observations ORDER BY timestamp DESC,id DESC LIMIT ? OFFSET ?', (limit, offset)).fetchall()
