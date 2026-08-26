"""
Pulls strength workouts from Hevy's official API into the unified DB.

Docs: https://api.hevyapp.com/docs/  (requires Hevy Pro for an API key,
generated at https://hevy.com/settings?developer)

This is the most reliable sync in the repo — it's a real, documented,
versioned REST API, not a scraped/unofficial one.
"""

import argparse
import json
import os
import sys

import requests
from dotenv import load_dotenv

from src.db import get_conn, init_db, mark_synced

load_dotenv()

BASE_URL = "https://api.hevyapp.com/v1"
PAGE_SIZE = 10  # Hevy's documented default/max page size for /workouts


def _headers() -> dict:
    api_key = os.environ.get("HEVY_API_KEY")
    if not api_key:
        raise RuntimeError("HEVY_API_KEY is not set. Add it to .env")
    # NOTE: verify this header name against https://api.hevyapp.com/docs/
    # if you get 401s — Hevy has used `api-key` historically.
    return {"api-key": api_key, "Accept": "application/json"}


def fetch_all_workouts() -> list[dict]:
    workouts = []
    page = 1
    while True:
        resp = requests.get(
            f"{BASE_URL}/workouts",
            headers=_headers(),
            params={"page": page, "pageSize": PAGE_SIZE},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        batch = payload.get("workouts", [])
        if not batch:
            break
        workouts.extend(batch)
        page += 1
        if page > payload.get("page_count", page):
            break
    return workouts


def upsert_workout(conn, workout: dict) -> None:
    session_id = f"hevy:{workout['id']}"
    conn.execute(
        """
        INSERT INTO strength_sessions (id, title, start_time_utc, duration_s, raw_json)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title = excluded.title,
            start_time_utc = excluded.start_time_utc,
            duration_s = excluded.duration_s,
            raw_json = excluded.raw_json,
            updated_at = datetime('now')
        """,
        (
            session_id,
            workout.get("title"),
            workout.get("start_time"),
            _duration_seconds(workout),
            json.dumps(workout),
        ),
    )

    for ex_index, exercise in enumerate(workout.get("exercises", [])):
        ex_name = exercise.get("title", f"exercise_{ex_index}")
        for set_index, s in enumerate(exercise.get("sets", [])):
            conn.execute(
                """
                INSERT INTO strength_sets (session_id, exercise, set_index, set_type, weight_kg, reps, rpe)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, exercise, set_index) DO UPDATE SET
                    set_type = excluded.set_type,
                    weight_kg = excluded.weight_kg,
                    reps = excluded.reps,
                    rpe = excluded.rpe
                """,
                (
                    session_id,
                    ex_name,
                    set_index,
                    s.get("type", "normal"),
                    s.get("weight_kg"),
                    s.get("reps"),
                    s.get("rpe"),
                ),
            )

    # Also mirror as a lightweight row in `activities` so cross-sport queries
    # (e.g. "everything I did this week") only need one table.
    conn.execute(
        """
        INSERT INTO activities (id, source, sport, name, start_time_utc, duration_s, raw_json)
        VALUES (?, 'hevy', 'strength_training', ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            start_time_utc = excluded.start_time_utc,
            duration_s = excluded.duration_s,
            updated_at = datetime('now')
        """,
        (session_id, workout.get("title"), workout.get("start_time"), _duration_seconds(workout), json.dumps(workout)),
    )


def _duration_seconds(workout: dict) -> int | None:
    start, end = workout.get("start_time"), workout.get("end_time")
    if not (start and end):
        return None
    from datetime import datetime

    fmt = "%Y-%m-%dT%H:%M:%S%z"
    try:
        return int((datetime.strptime(end, fmt) - datetime.strptime(start, fmt)).total_seconds())
    except ValueError:
        return None


def sync() -> int:
    init_db()
    workouts = fetch_all_workouts()
    with get_conn() as conn:
        for w in workouts:
            upsert_workout(conn, w)
    mark_synced("hevy", note=f"{len(workouts)} workouts")
    return len(workouts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspect", action="store_true", help="Print raw API response, don't write to DB")
    args = parser.parse_args()

    if args.inspect:
        data = fetch_all_workouts()
        print(json.dumps(data[:2], indent=2))
        print(f"\n...{len(data)} total workouts fetched")
        sys.exit(0)

    count = sync()
    print(f"Synced {count} Hevy workouts")
