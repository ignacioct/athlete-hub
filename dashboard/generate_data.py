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
from src.strength_progress import core_lift_1rm_history, recent_prs, weekly_split_status  # noqa: E402
from src.weekly_workouts import get_weekly_workouts  # noqa: E402

OUTPUT = Path(__file__).parent / "data.json"


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

        races = [dict(r) for r in conn.execute("SELECT * FROM races WHERE status = 'upcoming' ORDER BY date ASC").fetchall()]

        weekly_workouts = get_weekly_workouts(conn, date.today())

        # VO2 max only updates every few days, so the shared `days_back`
        # window (180d by default) leaves the trend chart sparse. It gets
        # its own year-long, non-null-only query instead of stretching
        # every other (daily) metric's window along with it.
        vo2max_history = [
            dict(r)
            for r in conn.execute(
                """
                SELECT date, vo2max_running
                FROM daily_metrics
                WHERE vo2max_running IS NOT NULL AND date >= ?
                ORDER BY date ASC
                """,
                ((date.today() - timedelta(days=365)).isoformat(),),
            ).fetchall()
        ]

        weekly_split = weekly_split_status(conn, date.today())
        core_lifts = core_lift_1rm_history(conn)
        prs = recent_prs(conn)

    OUTPUT.write_text(
        json.dumps(
            {
                "generated_at": date.today().isoformat(),
                "activities": activities,
                "daily_metrics": daily,
                "races": races,
                "weekly_workouts": weekly_workouts,
                "vo2max_history": vo2max_history,
                "weekly_split": weekly_split,
                "core_lifts": core_lifts,
                "recent_prs": prs,
            },
            indent=2,
            default=str,
        )
    )
    print(f"Wrote {OUTPUT} ({len(activities)} activities, {len(daily)} days, {len(races)} races, {len(weekly_workouts)} weekly workouts, {len(vo2max_history)} vo2max readings)")


if __name__ == "__main__":
    main()
