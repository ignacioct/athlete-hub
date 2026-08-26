"""
Unified SQLite schema for athlete-hub.

One database, four kinds of data:
  - activities: any logged session (run, ride, strength-tagged Garmin entry, etc.)
  - strength_sets: per-set detail for strength sessions, from Hevy
  - daily_metrics: one row per calendar day (HR, sleep, body battery, HRV, steps...)
  - races: upcoming events you want Claude to plan around
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DEFAULT_DB_PATH = os.environ.get("DB_PATH", "data/athlete.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS activities (
    id              TEXT PRIMARY KEY,      -- "garmin:<activityId>" or "intervals:<id>"
    source          TEXT NOT NULL,         -- 'garmin' | 'intervals'
    sport           TEXT,                  -- 'running' | 'strength_training' | 'cycling' | ...
    name            TEXT,
    start_time_utc  TEXT NOT NULL,         -- ISO-8601
    duration_s      INTEGER,
    distance_m      REAL,
    avg_hr          INTEGER,
    max_hr          INTEGER,
    calories        INTEGER,
    elevation_gain_m REAL,
    avg_pace_s_per_km REAL,
    training_load   REAL,                  -- e.g. Garmin's or intervals.icu's load score
    is_strength_duplicate INTEGER DEFAULT 0, -- 1 if this is the Garmin copy of a Hevy session
    raw_json        TEXT,                  -- original payload, for anything not modeled above
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS strength_sessions (
    id              TEXT PRIMARY KEY,      -- "hevy:<workoutId>"
    title           TEXT,
    start_time_utc  TEXT NOT NULL,
    duration_s      INTEGER,
    raw_json        TEXT,
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS strength_sets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES strength_sessions(id) ON DELETE CASCADE,
    exercise        TEXT NOT NULL,
    set_index       INTEGER,
    set_type        TEXT,                  -- 'normal' | 'warmup' | 'failure' | 'dropset'
    weight_kg       REAL,
    reps            INTEGER,
    rpe             REAL,
    UNIQUE(session_id, exercise, set_index)
);

CREATE TABLE IF NOT EXISTS daily_metrics (
    date            TEXT PRIMARY KEY,      -- YYYY-MM-DD
    resting_hr      INTEGER,
    avg_hr          INTEGER,
    hrv             REAL,
    sleep_score     INTEGER,
    sleep_duration_s INTEGER,
    body_battery_max INTEGER,
    body_battery_min INTEGER,
    steps           INTEGER,
    stress_avg      INTEGER,
    vo2max_running  REAL,
    weight_kg       REAL,
    ctl             REAL,                  -- from intervals.icu wellness (fitness)
    atl             REAL,                  -- from intervals.icu wellness (fatigue)
    form            REAL,                  -- ctl - atl
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS races (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    date            TEXT NOT NULL,         -- YYYY-MM-DD
    distance_km     REAL,
    priority        TEXT DEFAULT 'B',      -- 'A' | 'B' | 'C'
    goal_time       TEXT,                  -- e.g. "3:45:00"
    notes           TEXT,
    status          TEXT DEFAULT 'upcoming', -- 'upcoming' | 'done' | 'cancelled'
    intervals_event_id TEXT,               -- set once mirrored to intervals.icu calendar
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS planned_workouts (
    id              TEXT PRIMARY KEY,      -- "garmin_club:<workoutId>" or "intervals:<event id>"
    source          TEXT NOT NULL,         -- 'garmin_club' (club's TrainingPeaks->Garmin plan) | 'intervals' (create_workout)
    name            TEXT,
    date            TEXT NOT NULL,         -- YYYY-MM-DD
    sport           TEXT,
    is_rest_day     INTEGER DEFAULT 0,
    description     TEXT,                  -- intervals.icu structured-workout text, when present
    estimated_duration_s INTEGER,          -- Garmin's planned-duration estimate, when present
    raw_json        TEXT,
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sync_log (
    source          TEXT PRIMARY KEY,      -- 'garmin' | 'hevy' | 'intervals'
    last_synced_at  TEXT,
    last_status     TEXT,
    note            TEXT
);

CREATE INDEX IF NOT EXISTS idx_activities_start ON activities(start_time_utc);
CREATE INDEX IF NOT EXISTS idx_activities_sport ON activities(sport);
CREATE INDEX IF NOT EXISTS idx_sets_session ON strength_sets(session_id);
CREATE INDEX IF NOT EXISTS idx_planned_workouts_date ON planned_workouts(date);
CREATE INDEX IF NOT EXISTS idx_sets_exercise ON strength_sets(exercise);
"""


def get_db_path() -> str:
    path = os.environ.get("DB_PATH", DEFAULT_DB_PATH)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def get_conn(db_path: str | None = None):
    path = db_path or get_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str | None = None) -> None:
    with get_conn(db_path) as conn:
        conn.executescript(SCHEMA)


def mark_synced(source: str, status: str = "ok", note: str = "", db_path: str | None = None) -> None:
    with get_conn(db_path) as conn:
        conn.execute(
            """
            INSERT INTO sync_log (source, last_synced_at, last_status, note)
            VALUES (?, datetime('now'), ?, ?)
            ON CONFLICT(source) DO UPDATE SET
                last_synced_at = excluded.last_synced_at,
                last_status = excluded.last_status,
                note = excluded.note
            """,
            (source, status, note),
        )


if __name__ == "__main__":
    init_db()
    print(f"Initialized database at {get_db_path()}")
