"""
MCP server for athlete-hub. Exposes the local SQLite DB (Garmin + Hevy +
intervals.icu, unified) and the workout/race creation path to Claude.

Run standalone for testing:
    uv run mcp_server/server.py

Add to Claude Desktop / Claude Code config (see mcp_server/README.md).
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.mcpserver import MCPServer

from scripts.sync_all import main as run_sync_all
from src.db import get_conn, init_db
from src.intervals_sync import push_workout
from src.races import add_race, list_races, update_race_status
from src.weekly_workouts import get_weekly_workouts as _get_weekly_workouts

mcp = MCPServer("athlete-hub")


@mcp.tool()
def sync_now(days_back: int = 7) -> dict:
    """
    Pull fresh data from Garmin, Hevy (if configured), and intervals.icu into
    the local DB, then regenerate the dashboard snapshot. There's no cron job
    behind this repo — the sync machine isn't guaranteed to be on — so this
    tool (and the dashboard's "Sync now" button) is how syncs actually happen.

    Takes roughly 30-60s: Garmin's sync logs in via Selenium every time.
    days_back is the lookback window for Garmin/intervals.icu (default 7,
    plenty of overlap for routine use — only raise it for a backfill).

    Returns a dict of {source: result} — a per-source activity/day count on
    success, or "FAILED: <reason>" if that one source errored (other sources
    still sync; this never raises for a single-source failure).
    """
    return run_sync_all(days_back)


@mcp.tool()
def get_activities(start_date: str, end_date: str, sport: str | None = None) -> list[dict]:
    """
    Get logged activities (runs, rides, strength sessions) between two dates.

    Args:
        start_date: YYYY-MM-DD, inclusive
        end_date: YYYY-MM-DD, inclusive
        sport: optional filter, e.g. 'running', 'strength_training', 'cycling'

    Returns activities from both Garmin and intervals.icu. Garmin's own
    strength-training entries are excluded by default (is_strength_duplicate)
    since Hevy has the real per-set detail for those — use get_strength_sets
    for lifting data instead. Garmin's copy of a run/ride is also excluded
    whenever intervals.icu has the same activity (matched by start time,
    since intervals.icu mirrors your Garmin activities once connected) —
    intervals.icu's copy carries training-load data Garmin's doesn't.
    """
    init_db()
    query = """
        SELECT id, source, sport, name, start_time_utc, duration_s, distance_m,
               avg_hr, max_hr, calories, elevation_gain_m, avg_pace_s_per_km, training_load
        FROM activities
        WHERE start_time_utc >= ? AND start_time_utc <= ?
          AND is_strength_duplicate = 0
          AND NOT (
              source = 'garmin'
              AND EXISTS (
                  SELECT 1 FROM activities a2
                  WHERE a2.source = 'intervals'
                    AND ABS(strftime('%s', a2.start_time_utc) - strftime('%s', activities.start_time_utc)) < 600
              )
          )
    """
    params = [start_date, end_date + "T23:59:59"]
    if sport:
        query += " AND sport = ?"
        params.append(sport)
    query += " ORDER BY start_time_utc DESC"

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


@mcp.tool()
def get_daily_metrics(start_date: str, end_date: str) -> list[dict]:
    """
    Get daily health metrics: resting HR, HRV, sleep, body battery, steps,
    stress, VO2max, weight, and training load (CTL/ATL/form from
    intervals.icu). Covers both watches since they share one Garmin account.
    """
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM daily_metrics WHERE date >= ? AND date <= ? ORDER BY date ASC",
            (start_date, end_date),
        ).fetchall()
        return [dict(r) for r in rows]


@mcp.tool()
def get_strength_sets(exercise: str | None = None, start_date: str | None = None,
                       end_date: str | None = None, limit: int = 100) -> list[dict]:
    """
    Get individual lifting sets from Hevy, optionally filtered by exercise
    name (e.g. 'Back Squat (Barbell)') and/or date range. Ordered newest
    first. Use this to track weight/reps/RPE progression over time.
    """
    init_db()
    query = """
        SELECT s.exercise, s.set_index, s.set_type, s.weight_kg, s.reps, s.rpe,
               sess.start_time_utc, sess.title
        FROM strength_sets s
        JOIN strength_sessions sess ON sess.id = s.session_id
        WHERE 1=1
    """
    params = []
    if exercise:
        query += " AND s.exercise LIKE ?"
        params.append(f"%{exercise}%")
    if start_date:
        query += " AND sess.start_time_utc >= ?"
        params.append(start_date)
    if end_date:
        query += " AND sess.start_time_utc <= ?"
        params.append(end_date + "T23:59:59")
    query += " ORDER BY sess.start_time_utc DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


@mcp.tool()
def get_weekly_workouts() -> list[dict]:
    """
    Get every day of this week (Monday-Sunday), combining planned workouts
    with whatever was actually logged that day.

    Planned workouts come from two sources: your running club's
    TrainingPeaks -> Garmin schedule (source='garmin_club'), and anything
    created here via create_workout (source='intervals'). A day with no
    plan but a real logged activity still shows up (source='unplanned') —
    this covers every day, not just planned ones. Each item has a status:
    'done' (something was logged, planned or not), 'missed' (date has
    passed with nothing logged), 'today', 'upcoming', or 'rest'. When done,
    `actual` holds the matched activity's real distance/duration/pace/HR to
    compare against `estimated_duration_s` (the only numeric target Garmin's
    schedule reliably provides — plain-text workout descriptions aren't
    auto-parsed into numeric targets by intervals.icu).
    """
    init_db()
    with get_conn() as conn:
        return _get_weekly_workouts(conn, date.today())


@mcp.tool()
def get_race_calendar(status: str = "upcoming") -> list[dict]:
    """Get races. status is 'upcoming' (default), 'done', or 'cancelled'."""
    return list_races(status)


@mcp.tool()
def add_upcoming_race(name: str, date: str, distance_km: float | None = None,
                       priority: str = "B", goal_time: str | None = None,
                       notes: str = "") -> dict:
    """
    Add a future race so it can be taken into account for planning.

    Args:
        name: race name
        date: YYYY-MM-DD
        distance_km: race distance in km
        priority: 'A' (peak for this one), 'B' (train through, race hard),
                   or 'C' (low priority / tune-up race)
        goal_time: optional target finish time, e.g. "3:45:00"
        notes: anything else worth remembering (course profile, why it matters, etc.)

    Also mirrors the race onto your intervals.icu calendar (as a RACE_A/B/C
    event) so its training-load and taper guidance accounts for it too.
    """
    race_id = add_race(name, date, distance_km, priority, goal_time, notes)
    return {"race_id": race_id, "status": "added"}


@mcp.tool()
def mark_race_done(race_id: int) -> dict:
    """Mark a race as completed so it drops out of the upcoming list."""
    update_race_status(race_id, "done")
    return {"race_id": race_id, "status": "done"}


@mcp.tool()
def create_workout(name: str, date: str, sport_type: str, description: str) -> dict:
    """
    Create a structured workout and push it to your calendar. If Garmin is
    connected on intervals.icu with "Upload planned workouts" enabled, it
    syncs to your Forerunner automatically — usually within a few minutes.

    Args:
        name: short workout title, e.g. "Threshold intervals"
        date: YYYY-MM-DD, when the workout is scheduled
        sport_type: 'Run', 'Ride', 'WeightTraining', etc. (intervals.icu sport type)
        description: workout description. For structured steps, use
            intervals.icu's syntax, e.g.:
                "Warmup 15m Z2\\n6x(3m Z4, 2m Z1)\\nCooldown 10m Z1"
            Plain text also works but won't have structured pace/HR targets
            your watch can guide you through.
    """
    result = push_workout(name, date, sport_type, description)
    return {"intervals_event_id": result.get("id"), "status": "created"}


if __name__ == "__main__":
    mcp.run()
