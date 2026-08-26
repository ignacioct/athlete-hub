"""
Pulls strength workouts from Hevy into the unified DB.

Hevy's real, documented API (https://api.hevyapp.com/docs/) needs Hevy Pro
for an API key — not available on this account. Instead this wraps
https://pypi.org/project/hevy-unofficial/, a reverse-engineered client for
the same private API the mobile app itself uses, authenticated via a
session token instead of an API key.

Login is a one-time manual step, not something this module can do on its
own: hevy-unofficial supports an automated Playwright browser login, but
Google actively detects and blocks OAuth sign-ins from automated browsers,
so that path is unreliable for a Google-linked Hevy account (confirmed
against this account — the automated flow got its browser session closed
mid-login). Run `python scripts/hevy_login.py` once instead: it walks
through copying the `auth2.0-token` cookie out of a normal, non-automated
browser login, which Google has no reason to block. Tokens then cache to
~/.config/hevy-unofficial/credentials.json and auto-refresh, so this only
needs to happen again if the refresh token itself gets revoked.

Verified against a real export (2026-08-26) — the unofficial API's actual
field names differ from what the official API's docs describe, since this
is a different (private, mobile-app-facing) API entirely:
  - workout name is `name`, not `title`
  - `start_time`/`end_time` are Unix epoch seconds (int), not ISO strings
  - a set's warmup/normal/failure/dropset field is `indicator`, not `type`
  - /user_workouts_paged silently 400s on `limit` above 5 — hevy-unofficial's
    own iter_paged() defaults to page_size=10, which breaks immediately.
    PAGE_SIZE is 5 here for that reason; confirmed offset-based pagination
    doesn't overlap/skip at that size.
GARMIN_FIELD_MAP-style constants aren't used here since the shape is simple
enough that inline `.get()` calls stay readable — see HEVY_WORKOUT_FIELDS
below if that changes.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

from src.db import get_conn, init_db, mark_synced

load_dotenv()

PAGE_SIZE = 5  # /user_workouts_paged 400s above this — see module docstring


def _client():
    from hevy_unofficial import CredentialStore, HevyClient

    email = os.environ.get("HEVY_EMAIL")
    if not email:
        raise RuntimeError("HEVY_EMAIL is not set. Add it to .env")

    cached = CredentialStore().get(email)
    if not cached:
        raise RuntimeError(
            f"No cached Hevy credentials for {email}. Run: python scripts/hevy_login.py"
        )
    return HevyClient(
        access_token=cached.tokens.access_token,
        refresh_token=cached.tokens.refresh_token,
        user_id=cached.tokens.user_id,
        credential_email=email,
        credential_store=CredentialStore(),
    )


def fetch_all_workouts() -> list[dict]:
    client = _client()
    username = client.users.get_account()["username"]
    return list(client.workouts.iter_paged(username, page_size=PAGE_SIZE))


def _epoch_to_iso(seconds) -> str | None:
    """Unix epoch seconds -> naive-UTC ISO string, matching the convention
    the rest of this repo's start_time_utc columns already use (see
    garmin_sync.py's docstring)."""
    if seconds is None:
        return None
    return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _duration_seconds(workout: dict) -> int | None:
    start, end = workout.get("start_time"), workout.get("end_time")
    if start is None or end is None:
        return None
    return int(end - start)


def upsert_workout(conn, workout: dict) -> None:
    session_id = f"hevy:{workout['id']}"
    name = workout.get("name")
    start_iso = _epoch_to_iso(workout.get("start_time"))
    duration_s = _duration_seconds(workout)

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
        (session_id, name, start_iso, duration_s, json.dumps(workout)),
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
                    s.get("indicator", "normal"),
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
        (session_id, name, start_iso, duration_s, json.dumps(workout)),
    )


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
