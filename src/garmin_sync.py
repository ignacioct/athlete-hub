"""
Pulls Garmin Connect data (activities + daily health metrics from both your
Forerunner 255 and Circa, since they share one Garmin account) into the
unified DB through Garmin's official Personal API, using Garmin's own client
(https://github.com/garmin/connect-personal-api-python).

The Personal API is read-only and has no workout-calendar endpoint, so the
club's TrainingPeaks -> Garmin plan still comes from garmin-givemydata's
browser session (see fetch_workout_schedule()). VO2 max isn't exposed either;
intervals_sync.py fills it from intervals.icu's wellness data.

Field names below were checked against real responses on 2026-10-31.
"""

import argparse
import json
import os
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from garmin_personal_api import GarminPersonalApiClient, PersonalApiAuthenticator

from src.db import get_conn, init_db, mark_synced
from src.weekly_workouts import week_bounds

load_dotenv()

# Sleep summaries return HTTP 400 for ranges much longer than a month.
CHUNK_DAYS = 28
# Activity search returns at most 100 results per page, whatever limit you ask for.
PAGE_SIZE = 100


def _client() -> GarminPersonalApiClient:
    api_key = os.environ.get("GARMIN_PERSONAL_API_KEY")
    if not api_key:
        raise RuntimeError("GARMIN_PERSONAL_API_KEY is not set. Add it to .env")
    with PersonalApiAuthenticator() as auth:
        token = auth.obtain_token(api_key)
    return GarminPersonalApiClient(token.access_token)


def _chunks(start: date, end: date):
    while start <= end:
        chunk_end = min(start + timedelta(days=CHUNK_DAYS - 1), end)
        yield start, chunk_end
        start = chunk_end + timedelta(days=1)


def _nested(record: dict, *keys):
    for key in keys:
        record = record.get(key) if isinstance(record, dict) else None
    return record


def fetch_activities(client, start: date, end: date) -> list[dict]:
    activities: list[dict] = []
    while True:
        page = client.search_activities(
            start=len(activities), limit=PAGE_SIZE, start_date=start, end_date=end
        ) or []
        activities += page
        if len(page) < PAGE_SIZE:
            return activities


def fetch_wellness(client, start: date, end: date) -> dict[str, dict]:
    """Daily metrics keyed by calendar date, joined from several endpoints."""
    wellness: dict[str, dict] = {}

    def put(day: str | None, **fields) -> None:
        if day:
            wellness.setdefault(day, {}).update(
                {k: v for k, v in fields.items() if v is not None}
            )

    for s, e in _chunks(start, end):
        for r in (client.get_daily_summaries(s, e) or {}).get("data", []):
            put(
                r.get("calendarDate"),
                resting_hr=_nested(r, "heartRate", "restingValue"),
                steps=_nested(r, "movement", "steps", "value"),
                stress_avg=_nested(r, "stress", "avgLevel"),
                body_battery_max=_nested(r, "bodyBattery", "maxValue"),
                body_battery_min=_nested(r, "bodyBattery", "minValue"),
                avg_respiration=_nested(r, "respiration", "avgValue"),
                avg_spo2=_nested(r, "pulseOx", "avgValue"),
                lowest_spo2=_nested(r, "pulseOx", "minValue"),
            )

        for r in client.get_daily_sleep_summaries(s, e) or []:
            put(
                r.get("calendarDate"),
                sleep_score=_nested(r, "sleepScores", "overall", "value"),
                sleep_duration_s=r.get("sleepTimeSeconds"),
                deep_sleep_s=r.get("deepSleepSeconds"),
                light_sleep_s=r.get("lightSleepSeconds"),
                rem_sleep_s=r.get("remSleepSeconds"),
                awake_s=r.get("awakeSleepSeconds"),
            )

        for r in (client.get_daily_hrv_summaries(s, e) or {}).get("hrvSummaries", []):
            put(r.get("calendarDate"), hrv=r.get("lastNightAvg"))

        for r in (client.get_weight_measurements(s, e) or {}).get("dailyWeightSummaries", []):
            grams = _nested(r, "latestWeight", "weight")
            put(r.get("summaryDate"), weight_kg=grams / 1000 if grams is not None else None)

    return wellness


def sync_to_db(activities: list[dict], wellness: dict[str, dict]) -> tuple[int, int]:
    init_db()
    with get_conn() as conn:
        for a in activities:
            activity_id = a.get("activityId")
            if not activity_id:
                continue
            sport = str(_nested(a, "activityType", "typeKey") or "").lower()
            start_time = a.get("startTimeGMT")
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
                    a.get("activityName"),
                    start_time,
                    a.get("duration"),
                    a.get("distance"),
                    a.get("averageHR"),
                    a.get("maxHR"),
                    a.get("calories"),
                    a.get("elevationGain"),
                    a.get("activityTrainingLoad"),
                    # You log lifts in Garmin too (for HR) but Hevy has the
                    # real detail — flag Garmin's strength entries so
                    # queries can skip them and avoid double-counting.
                    1 if "strength" in sport else 0,
                    json.dumps(a),
                ),
            )

        # avg_hr and vo2max_running aren't written here: the Personal API has
        # no daily average HR, and VO2 max comes from intervals_sync.py.
        for d, w in wellness.items():
            conn.execute(
                """
                INSERT INTO daily_metrics (
                    date, resting_hr, hrv, sleep_score, sleep_duration_s,
                    body_battery_max, body_battery_min, steps, stress_avg,
                    weight_kg, avg_respiration, avg_spo2, lowest_spo2,
                    deep_sleep_s, light_sleep_s, rem_sleep_s, awake_s
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    resting_hr = excluded.resting_hr,
                    hrv = excluded.hrv,
                    sleep_score = excluded.sleep_score,
                    sleep_duration_s = excluded.sleep_duration_s,
                    body_battery_max = excluded.body_battery_max,
                    body_battery_min = excluded.body_battery_min,
                    steps = excluded.steps,
                    stress_avg = excluded.stress_avg,
                    weight_kg = COALESCE(excluded.weight_kg, daily_metrics.weight_kg),
                    avg_respiration = excluded.avg_respiration,
                    avg_spo2 = excluded.avg_spo2,
                    lowest_spo2 = excluded.lowest_spo2,
                    deep_sleep_s = excluded.deep_sleep_s,
                    light_sleep_s = excluded.light_sleep_s,
                    rem_sleep_s = excluded.rem_sleep_s,
                    awake_s = excluded.awake_s,
                    updated_at = datetime('now')
                """,
                (
                    d, w.get("resting_hr"), w.get("hrv"),
                    w.get("sleep_score"), w.get("sleep_duration_s"),
                    w.get("body_battery_max"), w.get("body_battery_min"),
                    w.get("steps"), w.get("stress_avg"), w.get("weight_kg"),
                    w.get("avg_respiration"), w.get("avg_spo2"), w.get("lowest_spo2"),
                    w.get("deep_sleep_s"), w.get("light_sleep_s"),
                    w.get("rem_sleep_s"), w.get("awake_s"),
                ),
            )

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
            date = excluded.date,
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


def fetch_workout_schedule(weeks_ahead: int = 2) -> list[dict]:
    """
    Fetch scheduled workouts (your running club's TrainingPeaks -> Garmin
    plan) from the Monday of this week through `weeks_ahead` weeks out.

    The Personal API has no calendar endpoint, so this is the one part of the
    Garmin sync that still goes through garmin-givemydata. It calls
    garmin_client.GarminClient's private _fetch_batch() to run a GraphQL query
    inside a logged-in Selenium session, reusing garmin_session.json when the
    cookies are still valid. If garmin_client's internals change this breaks,
    so every caller treats an exception or an empty list as "couldn't get it
    this time" rather than a hard failure.
    """
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    if not (email and password):
        return []

    from garmin_client import GarminClient

    monday, _ = week_bounds(date.today())
    end = date.today() + timedelta(weeks=weeks_ahead)
    query = (
        f'query{{workoutScheduleSummariesScalar('
        f'startDate:"{monday}", endDate:"{end.isoformat()}")}}'
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
    """Pulls the club's Garmin schedule into planned_workouts. Best-effort, see fetch_workout_schedule()."""
    init_db()
    try:
        records = fetch_workout_schedule(weeks_ahead)
    except Exception as e:
        print(f"Warning: could not fetch workout schedule: {e}")
        return 0

    with get_conn() as conn:
        for r in records:
            _upsert_planned_workout(conn, r)
    return len(records)


def _fetch(days_back: int) -> tuple[list[dict], dict[str, dict]]:
    end = date.today()
    start = end - timedelta(days=days_back)
    with _client() as client:
        return fetch_activities(client, start, end), fetch_wellness(client, start, end)


def sync(days_back: int = 90) -> tuple[int, int]:
    result = sync_to_db(*_fetch(days_back))
    try:
        n = sync_club_schedule()
        print(f"  club schedule: {n} planned workouts (this week + next 2)")
    except Exception as e:
        print(f"Warning: club schedule sync failed, skipping: {e}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspect", action="store_true", help="Fetch and print a sample of the mapped data, don't write to DB")
    parser.add_argument("--days", type=int, default=90)
    args = parser.parse_args()

    if args.inspect:
        activities, wellness = _fetch(args.days)
        print(f"{len(activities)} activities, {len(wellness)} wellness days\n")
        if activities:
            print("--- latest activity (raw) ---")
            print(json.dumps(activities[0], indent=2)[:1500])
        if wellness:
            latest = max(wellness)
            print(f"\n--- wellness {latest} (mapped) ---")
            print(json.dumps(wellness[latest], indent=2))
    else:
        n_act, n_well = sync(args.days)
        print(f"Synced {n_act} Garmin activities and {n_well} wellness days")
