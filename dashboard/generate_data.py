#!/usr/bin/env python3
"""
Dumps a snapshot of the DB to dashboard/data.json for the static dashboard
to read. scripts/sync_all.py already calls this after every sync — run it
standalone only if you want to refresh data.json without a full sync.
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import get_conn, init_db  # noqa: E402

OUTPUT = Path(__file__).parent / "data.json"


def _week_bounds(today: date) -> tuple[str, str]:
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()


def _weekly_workouts(conn, today: date) -> list[dict]:
    """This week's planned workouts (club's Garmin schedule + anything
    created via create_workout), each matched against a same-day completed
    activity if one exists, so the dashboard can show planned vs actual."""
    week_start, week_end = _week_bounds(today)
    today_str = today.isoformat()

    planned = [
        dict(r)
        for r in conn.execute(
            """
            SELECT id, source, name, date, sport, is_rest_day, description, estimated_duration_s
            FROM planned_workouts
            WHERE date >= ? AND date <= ?
            ORDER BY date ASC
            """,
            (week_start, week_end),
        ).fetchall()
    ]

    for w in planned:
        match = conn.execute(
            """
            SELECT source, name, duration_s, distance_m, avg_hr, avg_pace_s_per_km, training_load
            FROM activities
            WHERE date(start_time_utc) = ? AND is_strength_duplicate = 0
            ORDER BY (source = 'intervals') DESC
            LIMIT 1
            """,
            (w["date"],),
        ).fetchone()
        w["actual"] = dict(match) if match else None

        if w["is_rest_day"]:
            w["status"] = "rest"
        elif match:
            w["status"] = "done"
        elif w["date"] < today_str:
            w["status"] = "missed"
        elif w["date"] == today_str:
            w["status"] = "today"
        else:
            w["status"] = "upcoming"

    return planned


def main(days_back: int = 180) -> None:
    init_db()
    oldest = (date.today() - timedelta(days=days_back)).isoformat()

    with get_conn() as conn:
        activities = [
            dict(r)
            for r in conn.execute(
                """
                SELECT source, sport, name, start_time_utc, duration_s, distance_m,
                       avg_hr, training_load
                FROM activities
                WHERE start_time_utc >= ? AND is_strength_duplicate = 0
                  AND NOT (
                      source = 'garmin'
                      AND EXISTS (
                          SELECT 1 FROM activities a2
                          WHERE a2.source = 'intervals'
                            AND ABS(strftime('%s', a2.start_time_utc) - strftime('%s', activities.start_time_utc)) < 600
                      )
                  )
                ORDER BY start_time_utc ASC
                """,
                (oldest,),
            ).fetchall()
        ]

        daily = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM daily_metrics WHERE date >= ? ORDER BY date ASC",
                (oldest,),
            ).fetchall()
        ]

        strength = [
            dict(r)
            for r in conn.execute(
                """
                SELECT s.exercise, s.weight_kg, s.reps, sess.start_time_utc
                FROM strength_sets s
                JOIN strength_sessions sess ON sess.id = s.session_id
                WHERE sess.start_time_utc >= ?
                ORDER BY sess.start_time_utc ASC
                """,
                (oldest,),
            ).fetchall()
        ]

        races = [dict(r) for r in conn.execute("SELECT * FROM races WHERE status = 'upcoming' ORDER BY date ASC").fetchall()]

        weekly_workouts = _weekly_workouts(conn, date.today())

    OUTPUT.write_text(
        json.dumps(
            {
                "generated_at": date.today().isoformat(),
                "activities": activities,
                "daily_metrics": daily,
                "strength_sets": strength,
                "races": races,
                "weekly_workouts": weekly_workouts,
            },
            indent=2,
            default=str,
        )
    )
    print(f"Wrote {OUTPUT} ({len(activities)} activities, {len(daily)} days, {len(strength)} sets, {len(races)} races, {len(weekly_workouts)} weekly workouts)")


if __name__ == "__main__":
    main()
