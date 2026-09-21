import sqlite3
import os

SCHEMA = """
CREATE TABLE IF NOT EXISTS locations (
    name TEXT PRIMARY KEY,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    queue_length INTEGER NOT NULL CHECK(queue_length >= 0),
    service_rate REAL NOT NULL CHECK(service_rate > 0),
    wait_minutes REAL NOT NULL CHECK(wait_minutes >= 0)
)
"""


def connect(path: str = "queuesense.db") -> sqlite3.Connection:
    path = os.getenv("QUEUESENSE_DB", path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def add_observation(conn, location, timestamp, queue_length, service_rate, wait_minutes):
    conn.execute("INSERT OR IGNORE INTO locations(name) VALUES (?)", (location,))
    cur = conn.execute(
        "INSERT INTO observations(location,timestamp,queue_length,service_rate,wait_minutes) VALUES (?,?,?,?,?)",
        (location, timestamp, queue_length, service_rate, wait_minutes),
    )
    conn.commit()
    return cur.lastrowid


def rows(conn):
    return conn.execute("SELECT * FROM observations ORDER BY timestamp").fetchall()


def locations(conn):
    return conn.execute("SELECT name FROM locations WHERE active=1 ORDER BY name").fetchall()


def recent_rows(conn, limit=100, offset=0):
    return conn.execute("SELECT * FROM observations ORDER BY timestamp DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
