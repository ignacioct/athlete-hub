"""
Shared deduped-activities query.

Garmin and intervals.icu both sync the same real-world runs once
intervals.icu is connected — the query below excludes Garmin's copy
whenever an intervals.icu activity exists within 10 minutes of it (see
mcp_server.get_activities' docstring for the full reasoning: intervals.icu's
copy carries training-load data Garmin's doesn't). This used to be
copy-pasted separately in mcp_server/server.py and dashboard/generate_data.py
— a third near-identical copy for race_readiness.py's weekly-volume
calculation would have been exactly the kind of drift that already caused a
real bug once this session (see weekly_workouts.py's git history), so it
lives here once instead.
"""

_COLUMNS = (
    "id, source, sport, name, start_time_utc, duration_s, distance_m, "
    "avg_hr, max_hr, calories, elevation_gain_m, avg_pace_s_per_km, training_load"
)

_DEDUP_CLAUSE = """
    is_strength_duplicate = 0
    AND NOT (
        source = 'garmin'
        AND EXISTS (
            SELECT 1 FROM activities a2
            WHERE a2.source = 'intervals'
              AND ABS(strftime('%s', a2.start_time_utc) - strftime('%s', activities.start_time_utc)) < 600
        )
    )
"""


def get_deduped_activities(
    conn,
    start_date: str,
    end_date: str | None = None,
    *,
    sport: str | None = None,
    sport_like: str | None = None,
    desc: bool = False,
):
    """start_date/end_date compare directly against start_time_utc — pass a
    full ISO timestamp (e.g. end_date + "T23:59:59") for end-of-day
    inclusivity if that matters to the caller."""
    query = f"SELECT {_COLUMNS} FROM activities WHERE start_time_utc >= ? AND {_DEDUP_CLAUSE}"
    params = [start_date]
    if end_date:
        query += " AND start_time_utc <= ?"
        params.append(end_date)
    if sport:
        query += " AND sport = ?"
        params.append(sport)
    if sport_like:
        query += " AND sport LIKE ?"
        params.append(f"%{sport_like}%")
    query += f" ORDER BY start_time_utc {'DESC' if desc else 'ASC'}"
    return conn.execute(query, params).fetchall()
