"""
Pulls Garmin Connect data (activities + daily health metrics from both your
Forerunner 255 and Circa, since they share one Garmin account) into the
unified DB.

Garmin has no personal API — see README for why. This wraps
https://github.com/nrvim/garmin-givemydata, currently the best-maintained
unofficial exporter, instead of re-implementing Garmin auth/scraping here.

Verified against a real export (2026-08-26) — garmin-givemydata's actual
shape differs from what a first pass at the docs suggested in a few ways:

- It's two separate phases, not one. `--days N` (fetch, logs in via
  Selenium, writes to its own local `garmin.db`) and `--export DIR` (dumps
  that local DB to CSV/JSON, no login) are independent — passing both flags
  to one invocation silently ignores `--days` and just exports whatever's
  already in `garmin.db`. run_export() below shells out twice.
- Files land in `<export dir>/json/`, one file per table (e.g.
  `activity.json`, `daily_summary.json`, `sleep.json`, `hrv.json`,
  `heart_rate.json`, `vo2max.json`, `weight.json`...) — there's no single
  combined "wellness" blob, so WELLNESS_SOURCES below joins several files by
  date instead of reading one.
- Every table also ships flattened, already-renamed `__`-prefixed
  convenience keys (`__average_hr`, `__calendar_date`, etc.) alongside the
  raw Garmin Connect API fields — those are what's mapped below since
  they're stable and self-describing.
- It also writes `garmin.db`, `garmin_session.json` (session cookies), and
  `debug.log` to the current working directory (not into `data/`) —
  gitignored, but worth knowing about if you go looking for them.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

from src.db import get_conn, init_db, mark_synced

load_dotenv()

EXPORT_DIR = Path("data/garmin_export")
EXPORT_JSON_DIR = EXPORT_DIR / "json"

# --- Adjust these after running --inspect against your real export ---------
GARMIN_FIELD_MAP = {
    "activity_id": "__activity_id",
    "sport": "__activity_type",       # e.g. "running", "strength_training"
    "name": "__activity_name",
    "start_time": "__start_time_gmt",  # "YYYY-MM-DD HH:MM:SS", GMT
    "duration_s": "__duration_seconds",
    "distance_m": "__distance_meters",
    "avg_hr": "__average_hr",
    "max_hr": "__max_hr",
    "calories": "__calories",
    "elevation_gain_m": "__elevation_gain",
    "training_load": "__training_load",
}

# garmin-givemydata exports one file per daily-metric table rather than a
# single "wellness" record, so we join several files by __calendar_date.
# {export filename: {db_field: source_key}}
WELLNESS_SOURCES: dict[str, dict[str, str]] = {
    "daily_summary.json": {
        "resting_hr": "__resting_heart_rate",
        "steps": "__total_steps",
        "stress_avg": "__average_stress_level",
        "body_battery_max": "__body_battery_highest",
        "body_battery_min": "__body_battery_lowest",
    },
    "heart_rate.json": {
        "avg_hr": "__avg_hr",
        "resting_hr": "__resting_hr",  # falls back to this if daily_summary lacks it
    },
    "sleep.json": {
        "sleep_score": "__sleep_score_overall",
        "sleep_duration_s": "__sleep_time_seconds",
    },
    "hrv.json": {
        "hrv": "__last_night_avg",
    },
    "weight.json": {
        "weight_kg": "__weight",  # grams in the export; converted in _merge_wellness
    },
}
WELLNESS_DATE_KEY = "__calendar_date"
# ---------------------------------------------------------------------------


def run_export(days_back: int = 90, profile: str = "all") -> None:
    """
    Refreshes the local export directory via garmin-givemydata.

    Two phases, since --days and --export can't be combined in one call
    (see module docstring): fetch fresh data into garmin-givemydata's own
    local DB, then export that DB to JSON/CSV.
    """
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    if not (email and password):
        raise RuntimeError("GARMIN_EMAIL / GARMIN_PASSWORD not set. Add them to .env")

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "GARMIN_EMAIL": email, "GARMIN_PASSWORD": password}

    subprocess.run(
        [
            "garmin-givemydata",
            "--profile", profile,
            "--days", str(days_back),
            "--no-files",  # skip FIT/GPS downloads; this repo's schema doesn't use them
        ],
        env=env,
        check=True,
    )
    subprocess.run(
        ["garmin-givemydata", "--export", str(EXPORT_DIR)],
        env=env,
        check=True,
    )


def _load_json_files(filename: str) -> list[dict]:
    path = EXPORT_JSON_DIR / filename
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else [data]


def _extract(record: dict, field_map: dict, key: str):
    source_key = field_map.get(key)
    return record.get(source_key) if source_key else None


def _merge_wellness() -> dict[str, dict]:
    """Join garmin-givemydata's per-metric daily export files by date."""
    wellness: dict[str, dict] = {}
    for filename, field_map in WELLNESS_SOURCES.items():
        for record in _load_json_files(filename):
            d = record.get(WELLNESS_DATE_KEY)
            if not d:
                continue
            row = wellness.setdefault(d, {})
            for db_field, source_key in field_map.items():
                if db_field in row and row[db_field] is not None:
                    continue  # earlier source in dict order wins
                value = record.get(source_key)
                if value is not None:
                    row[db_field] = value

    for record in _load_json_files("vo2max.json"):
        d = record.get(WELLNESS_DATE_KEY)
        if d and record.get("__sport") == "RUNNING":
            wellness.setdefault(d, {})["vo2max_running"] = record.get("__value")

    for row in wellness.values():
        if row.get("weight_kg") is not None:
            row["weight_kg"] = row["weight_kg"] / 1000  # grams -> kg

    return wellness


def sync_to_db() -> tuple[int, int]:
    init_db()
    activities = _load_json_files("activity.json")
    wellness = _merge_wellness()

    with get_conn() as conn:
        for a in activities:
            activity_id = _extract(a, GARMIN_FIELD_MAP, "activity_id")
            if not activity_id:
                continue
            sport = str(_extract(a, GARMIN_FIELD_MAP, "sport") or "").lower()
            start_time = _extract(a, GARMIN_FIELD_MAP, "start_time")
            if start_time:
                start_time = start_time.replace(" ", "T")  # "YYYY-MM-DD HH:MM:SS" -> ISO-ish
            conn.execute(
                """
                INSERT INTO activities (
                    id, source, sport, name, start_time_utc, duration_s, distance_m,
                    avg_hr, max_hr, calories, elevation_gain_m, training_load,
                    is_strength_duplicate, raw_json
                ) VALUES (?, 'garmin', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    training_load = excluded.training_load,
                    raw_json = excluded.raw_json,
                    updated_at = datetime('now')
                """,
                (
                    f"garmin:{activity_id}",
                    sport,
                    _extract(a, GARMIN_FIELD_MAP, "name"),
                    start_time,
                    _extract(a, GARMIN_FIELD_MAP, "duration_s"),
                    _extract(a, GARMIN_FIELD_MAP, "distance_m"),
                    _extract(a, GARMIN_FIELD_MAP, "avg_hr"),
                    _extract(a, GARMIN_FIELD_MAP, "max_hr"),
                    _extract(a, GARMIN_FIELD_MAP, "calories"),
                    _extract(a, GARMIN_FIELD_MAP, "elevation_gain_m"),
                    _extract(a, GARMIN_FIELD_MAP, "training_load"),
                    # You log lifts in Garmin too (for HR) but Hevy has the
                    # real detail — flag Garmin's strength entries so
                    # queries can skip them and avoid double-counting.
                    1 if "strength" in sport else 0,
                    json.dumps(a),
                ),
            )

        for d, w in wellness.items():
            conn.execute(
                """
                INSERT INTO daily_metrics (
                    date, resting_hr, avg_hr, hrv, sleep_score, sleep_duration_s,
                    body_battery_max, body_battery_min, steps, stress_avg,
                    vo2max_running, weight_kg
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    resting_hr = excluded.resting_hr,
                    avg_hr = excluded.avg_hr,
                    hrv = excluded.hrv,
                    sleep_score = excluded.sleep_score,
                    sleep_duration_s = excluded.sleep_duration_s,
                    body_battery_max = excluded.body_battery_max,
                    body_battery_min = excluded.body_battery_min,
                    steps = excluded.steps,
                    stress_avg = excluded.stress_avg,
                    vo2max_running = excluded.vo2max_running,
                    weight_kg = COALESCE(excluded.weight_kg, daily_metrics.weight_kg),
                    updated_at = datetime('now')
                """,
                (
                    d, w.get("resting_hr"), w.get("avg_hr"), w.get("hrv"),
                    w.get("sleep_score"), w.get("sleep_duration_s"),
                    w.get("body_battery_max"), w.get("body_battery_min"),
                    w.get("steps"), w.get("stress_avg"),
                    w.get("vo2max_running"), w.get("weight_kg"),
                ),
            )

        # workout_schedule.json only covers the backward-looking --days window
        # (see fetch_future_workout_schedule() for why forward dates need a
        # separate direct-API call), but it's the only way to see *past*
        # scheduled workouts — e.g. earlier this week — so both matter.
        for r in _load_json_files("workout_schedule.json"):
            _upsert_planned_workout(conn, r)

    mark_synced("garmin", note=f"{len(activities)} activities, {len(wellness)} wellness days")
    return len(activities), len(wellness)


def _upsert_planned_workout(conn, r: dict) -> None:
    d = r.get("scheduleDate")
    if not d:
        return
    workout_id = r.get("workoutId")
    conn.execute(
        """
        INSERT INTO planned_workouts (
            id, source, name, date, sport, is_rest_day,
            estimated_duration_s, raw_json
        ) VALUES (?, 'garmin_club', ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            sport = excluded.sport,
            is_rest_day = excluded.is_rest_day,
            estimated_duration_s = excluded.estimated_duration_s,
            raw_json = excluded.raw_json,
            updated_at = datetime('now')
        """,
        (
            f"garmin_club:{workout_id or d}",
            r.get("workoutName"),
            d,
            r.get("workoutType"),
            1 if r.get("isRestDay") else 0,
            r.get("estimatedDurationInSecs"),
            json.dumps(r),
        ),
    )


def fetch_future_workout_schedule(weeks_ahead: int = 2) -> list[dict]:
    """
    Fetch FUTURE-dated workout_schedule entries — your running club's
    TrainingPeaks -> Garmin plan — directly via Garmin's private GraphQL
    endpoint. garmin-givemydata's own CLI can't do this: every one of its
    fetch modes hardcodes end_date=today (see module docstring), so there's
    no --days/--since combination that reaches forward in time.

    This is meaningfully more fragile than the rest of this file: it reaches
    into garmin_client.GarminClient's *private* (underscore-prefixed)
    _fetch_batch() method — the same mechanism garmin-givemydata's CLI uses
    internally for GraphQL queries (a real browser fetch() call with a CSRF
    token, run via Selenium's execute_async_script) — because there's no
    public API for an arbitrary future-dated query. It reuses the same
    session cookies the regular sync already established, so it should log
    in instantly rather than prompting again. If garmin_client's internals
    change, this breaks silently; that's why every call site wraps it and
    treats an empty list / exception as "couldn't get it this time" rather
    than a hard failure.
    """
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    if not (email and password):
        return []

    from garmin_client import GarminClient

    today = date.today()
    end = today + timedelta(weeks=weeks_ahead)
    query = (
        f'query{{workoutScheduleSummariesScalar('
        f'startDate:"{today.isoformat()}", endDate:"{end.isoformat()}")}}'
    )

    client = GarminClient(
        email=email,
        password=password,
        profile_dir=Path("browser_profile"),
        headless=True,
        session_file=Path("garmin_session.json"),
    )
    try:
        if not client.login():
            return []
        result = client._fetch_batch({}, {"future_workout_schedule": query})
        entry = result.get("gql_future_workout_schedule", {})
        if entry.get("status") != 200:
            return []
        records = entry.get("data", {}).get("data", {}).get("workoutScheduleSummariesScalar")
        return records if isinstance(records, list) else []
    finally:
        client.close()


def sync_club_schedule(weeks_ahead: int = 2) -> int:
    """Pulls the club's future-dated Garmin schedule into planned_workouts. Best-effort — see fetch_future_workout_schedule()."""
    init_db()
    try:
        records = fetch_future_workout_schedule(weeks_ahead)
    except Exception as e:
        print(f"Warning: could not fetch future workout schedule: {e}")
        return 0

    with get_conn() as conn:
        for r in records:
            _upsert_planned_workout(conn, r)
    return len(records)


def sync(days_back: int = 90) -> tuple[int, int]:
    run_export(days_back)
    result = sync_to_db()
    try:
        n = sync_club_schedule()
        print(f"  club schedule: {n} planned workouts (next 2 weeks)")
    except Exception as e:
        print(f"Warning: club schedule sync failed, skipping: {e}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspect", action="store_true", help="Run export and print raw structure, don't write to DB")
    parser.add_argument("--days", type=int, default=90)
    args = parser.parse_args()

    if args.inspect:
        run_export(args.days)
        files = sorted(EXPORT_JSON_DIR.glob("*.json"))
        print(f"Export produced {len(files)} JSON file(s) in {EXPORT_JSON_DIR}:\n")
        for f in [p for p in files if p.name in ("activity.json", "daily_summary.json", "sleep.json", "hrv.json", "heart_rate.json", "vo2max.json", "weight.json")]:
            print(f"--- {f.name} ---")
            content = json.loads(f.read_text())
            sample = content[0] if isinstance(content, list) and content else content
            print(json.dumps(sample, indent=2)[:1500])
            print()
        print("Compare these keys against GARMIN_FIELD_MAP / WELLNESS_SOURCES at the top of this file.")
        sys.exit(0)

    n_act, n_well = sync(args.days)
    print(f"Synced {n_act} Garmin activities and {n_well} wellness days")
