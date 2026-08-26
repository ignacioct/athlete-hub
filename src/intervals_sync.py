"""
Two-way integration with intervals.icu's official REST API.

READ path: pulls activities + wellness (which already includes computed
CTL/ATL/form) into the unified DB — this is a second, richer view of your
running data beyond raw Garmin numbers.

WRITE path: this is the important one. Rather than trying to write
structured workouts to Garmin directly (unofficial, unreliable), we create
the workout/race as a calendar event on intervals.icu. If you've ticked
"Upload planned workouts" under intervals.icu's Garmin connection settings,
intervals.icu pushes it to your watch for you. Same goes for races: adding
one here as a RACE_A/B/C event puts it on your intervals.icu calendar, which
its fitness/form charts and taper guidance already understand.

Docs: https://intervals.icu/api  (Settings -> Developer Settings for your
Athlete ID and API key)
"""

import json
import os
from datetime import date, datetime, timedelta

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from src.db import get_conn, init_db, mark_synced

load_dotenv()

BASE_URL = "https://intervals.icu/api/v1"


def _athlete_id() -> str:
    aid = os.environ.get("INTERVALS_ATHLETE_ID")
    if not aid:
        raise RuntimeError("INTERVALS_ATHLETE_ID is not set. Add it to .env")
    return aid


def _auth() -> HTTPBasicAuth:
    key = os.environ.get("INTERVALS_API_KEY")
    if not key:
        raise RuntimeError("INTERVALS_API_KEY is not set. Add it to .env")
    return HTTPBasicAuth("API_KEY", key)


def fetch_activities(oldest: str, newest: str) -> list[dict]:
    resp = requests.get(
        f"{BASE_URL}/athlete/{_athlete_id()}/activities",
        auth=_auth(),
        params={"oldest": oldest, "newest": newest},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_wellness(oldest: str, newest: str) -> list[dict]:
    resp = requests.get(
        f"{BASE_URL}/athlete/{_athlete_id()}/wellness",
        auth=_auth(),
        params={"oldest": oldest, "newest": newest},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def pull_to_db(days_back: int = 90) -> tuple[int, int]:
    init_db()
    oldest = (date.today() - timedelta(days=days_back)).isoformat()
    newest = date.today().isoformat()

    activities = fetch_activities(oldest, newest)
    wellness = fetch_wellness(oldest, newest)

    with get_conn() as conn:
        for a in activities:
            conn.execute(
                """
                INSERT INTO activities (
                    id, source, sport, name, start_time_utc, duration_s, distance_m,
                    avg_hr, max_hr, calories, elevation_gain_m, avg_pace_s_per_km,
                    training_load, raw_json
                ) VALUES (?, 'intervals', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    training_load = excluded.training_load,
                    raw_json = excluded.raw_json,
                    updated_at = datetime('now')
                """,
                (
                    f"intervals:{a['id']}",
                    a.get("type"),
                    a.get("name"),
                    a.get("start_date_local"),
                    a.get("moving_time"),
                    a.get("distance"),
                    a.get("average_heartrate"),
                    a.get("max_heartrate"),
                    a.get("calories"),
                    a.get("total_elevation_gain"),
                    _pace_s_per_km(a),
                    a.get("icu_training_load"),
                    json.dumps(a),
                ),
            )

        for w in wellness:
            d = w.get("id")  # wellness entries are keyed by date (YYYY-MM-DD)
            if not d:
                continue
            conn.execute(
                """
                INSERT INTO daily_metrics (date, resting_hr, hrv, sleep_score, weight_kg, ctl, atl, form)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    resting_hr = COALESCE(excluded.resting_hr, daily_metrics.resting_hr),
                    hrv = COALESCE(excluded.hrv, daily_metrics.hrv),
                    sleep_score = COALESCE(excluded.sleep_score, daily_metrics.sleep_score),
                    weight_kg = COALESCE(excluded.weight_kg, daily_metrics.weight_kg),
                    ctl = excluded.ctl,
                    atl = excluded.atl,
                    form = excluded.form,
                    updated_at = datetime('now')
                """,
                (
                    d,
                    w.get("restingHR"),
                    w.get("hrv"),
                    w.get("sleepScore"),
                    w.get("weight"),
                    w.get("ctl"),
                    w.get("atl"),
                    (w.get("ctl") - w.get("atl")) if w.get("ctl") is not None and w.get("atl") is not None else None,
                ),
            )

    mark_synced("intervals", note=f"{len(activities)} activities, {len(wellness)} wellness days")
    return len(activities), len(wellness)


def _pace_s_per_km(activity: dict) -> float | None:
    dist_m, moving_s = activity.get("distance"), activity.get("moving_time")
    if not dist_m or not moving_s:
        return None
    return moving_s / (dist_m / 1000)


def _as_datetime_local(date_local: str) -> str:
    """intervals.icu's /events endpoint rejects a bare YYYY-MM-DD date with a
    DateTimeParseException — it needs a full local datetime. Callers/docstrings
    throughout this repo use plain dates, so we pad here rather than push that
    detail out to every caller."""
    return date_local if "T" in date_local else f"{date_local}T00:00:00"


def push_workout(name: str, date_local: str, sport_type: str, description: str, uid: str | None = None) -> dict:
    """
    Create (or update, if uid is reused) a planned workout on the intervals.icu
    calendar. If Garmin is connected there with "Upload planned workouts"
    ticked, this shows up on the watch automatically.

    description supports intervals.icu's structured workout syntax, e.g.:
        "Warmup 10m Z2\n6x(4m Z4, 3m Z2)\nCooldown 10m Z2"
    Plain text also works, it just won't have structured steps/targets.
    """
    payload = {
        "category": "WORKOUT",
        "name": name,
        "start_date_local": _as_datetime_local(date_local),
        "type": sport_type,  # 'Run', 'Ride', 'WeightTraining', etc.
        "description": description,
    }
    if uid:
        payload["external_id"] = uid

    resp = requests.post(
        f"{BASE_URL}/athlete/{_athlete_id()}/events",
        auth=_auth(),
        params={"upsertOnUid": "true"} if uid else {},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def push_race(name: str, date_local: str, priority: str = "B", distance_km: float | None = None, notes: str = "") -> dict:
    """Create a race event on the intervals.icu calendar (category RACE_A/B/C)."""
    category = f"RACE_{priority.upper()}" if priority.upper() in ("A", "B", "C") else "RACE_B"
    description = notes
    if distance_km:
        description = f"{distance_km} km. {notes}".strip()

    payload = {
        "category": category,
        "name": name,
        "start_date_local": _as_datetime_local(date_local),
        "description": description,
        "type": "Run",  # required by intervals.icu for RACE_* categories; this repo is running-focused
    }
    resp = requests.post(
        f"{BASE_URL}/athlete/{_athlete_id()}/events",
        auth=_auth(),
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("--inspect", action="store_true", help="Print raw API responses, don't write to DB")
    parser.add_argument("--days", type=int, default=90)
    args = parser.parse_args()

    if args.inspect:
        oldest = (date.today() - timedelta(days=args.days)).isoformat()
        newest = date.today().isoformat()

        activities = fetch_activities(oldest, newest)
        print(f"--- {len(activities)} activities ---")
        print(json.dumps(activities[:2], indent=2)[:2000])

        wellness = fetch_wellness(oldest, newest)
        print(f"\n--- {len(wellness)} wellness days ---")
        print(json.dumps(wellness[:2], indent=2)[:2000])

        print("\nCompare these keys against the field access in pull_to_db() above.")
        sys.exit(0)

    n_act, n_well = pull_to_db(args.days)
    print(f"Synced {n_act} intervals.icu activities and {n_well} wellness days")
