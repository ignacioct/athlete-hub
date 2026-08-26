"""
MCP server for athlete-hub. Exposes the local SQLite DB (Garmin + Hevy +
intervals.icu, unified) and the workout/race creation path to Claude.

Run standalone for testing:
    python mcp_server/server.py

Add to Claude Desktop / Claude Code config (see mcp_server/README.md).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.mcpserver import MCPServer

from src.db import get_conn, init_db
from src.intervals_sync import push_workout
from src.races import add_race, list_races, update_race_status

mcp = MCPServer("athlete-hub")


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
    for lifting data instead.
    """
    init_db()
    query = """
        SELECT id, source, sport, name, start_time_utc, duration_s, distance_m,
               avg_hr, max_hr, calories, elevation_gain_m, avg_pace_s_per_km, training_load
        FROM activities
        WHERE start_time_utc >= ? AND start_time_utc <= ?
          AND is_strength_duplicate = 0
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
