"""
Day-by-day view of the current week (Monday-Sunday), combining planned
workouts with whatever was actually logged — shared by dashboard/generate_data.py
and mcp_server/server.py's get_weekly_workouts tool so the two can't drift
out of sync with each other.
"""

from datetime import date, timedelta


def week_bounds(today: date) -> tuple[str, str]:
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()


def _best_activity_match(conn, day: str):
    """The day's most significant logged activity, if any. Prefers
    intervals.icu's copy (richer/deduped, same reasoning as get_activities'
    dedup) and, among same-day activities (e.g. a run plus incidental
    walks), prefers the one with the highest training load — the real
    session, not a walk to the shops."""
    row = conn.execute(
        """
        SELECT source, name, sport, duration_s, distance_m, avg_hr, avg_pace_s_per_km, training_load
        FROM activities
        WHERE date(start_time_utc) = ? AND is_strength_duplicate = 0
        ORDER BY (source = 'intervals') DESC, COALESCE(training_load, -1) DESC
        LIMIT 1
        """,
        (day,),
    ).fetchone()
    return dict(row) if row else None


def get_weekly_workouts(conn, today: date) -> list[dict]:
    """Combines planned workouts (club's Garmin schedule + anything created
    via create_workout) with actual activities for every day this week —
    including days with no plan at all, so a real unplanned run still shows
    up rather than only appearing when it happens to match a planned entry."""
    week_start, week_end = week_bounds(today)
    today_str = today.isoformat()

    planned_by_date = {
        r["date"]: dict(r)
        for r in conn.execute(
            """
            SELECT id, source, name, date, sport, is_rest_day, description, estimated_duration_s
            FROM planned_workouts
            WHERE date >= ? AND date <= ?
            """,
            (week_start, week_end),
        ).fetchall()
    }

    result = []
    d = date.fromisoformat(week_start)
    end = date.fromisoformat(week_end)
    while d <= end:
        d_str = d.isoformat()
        plan = planned_by_date.get(d_str)
        actual = _best_activity_match(conn, d_str)

        if plan:
            entry = plan
            entry["actual"] = actual
            if plan["is_rest_day"]:
                entry["status"] = "rest"
            elif actual:
                entry["status"] = "done"
            elif d_str < today_str:
                entry["status"] = "missed"
            elif d_str == today_str:
                entry["status"] = "today"
            else:
                entry["status"] = "upcoming"
        elif actual:
            entry = {
                "id": f"unplanned:{d_str}", "source": "unplanned",
                "name": actual.get("name") or actual.get("sport") or "Workout",
                "date": d_str, "sport": actual.get("sport"), "is_rest_day": 0,
                "description": None, "estimated_duration_s": None,
                "actual": actual, "status": "done",
            }
        else:
            entry = {
                "id": f"empty:{d_str}", "source": None, "name": None,
                "date": d_str, "sport": None, "is_rest_day": 0,
                "description": None, "estimated_duration_s": None,
                "actual": None,
                "status": "missed" if d_str < today_str else ("today" if d_str == today_str else "upcoming"),
            }

        result.append(entry)
        d += timedelta(days=1)

    return result
