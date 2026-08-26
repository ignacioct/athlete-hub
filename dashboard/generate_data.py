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

    OUTPUT.write_text(
        json.dumps(
            {
                "generated_at": date.today().isoformat(),
                "activities": activities,
                "daily_metrics": daily,
                "strength_sets": strength,
                "races": races,
            },
            indent=2,
            default=str,
        )
    )
    print(f"Wrote {OUTPUT} ({len(activities)} activities, {len(daily)} days, {len(strength)} sets, {len(races)} races)")


if __name__ == "__main__":
    main()
