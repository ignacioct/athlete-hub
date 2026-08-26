"""
Local CRUD for upcoming races, with optional mirroring to the intervals.icu
calendar so its training-load/taper view knows about them too.
"""

from src.db import get_conn, init_db
from src.intervals_sync import push_race


def add_race(name: str, race_date: str, distance_km: float | None = None,
             priority: str = "B", goal_time: str | None = None,
             notes: str = "", sync_to_intervals: bool = True) -> int:
    init_db()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO races (name, date, distance_km, priority, goal_time, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, race_date, distance_km, priority, goal_time, notes),
        )
        race_id = cur.lastrowid

        if sync_to_intervals:
            try:
                event = push_race(name, race_date, priority, distance_km, notes)
                conn.execute(
                    "UPDATE races SET intervals_event_id = ? WHERE id = ?",
                    (str(event.get("id")), race_id),
                )
            except Exception as e:  # don't fail the whole add_race over a network hiccup
                print(f"Warning: could not mirror race to intervals.icu: {e}")

        return race_id


def list_races(status: str = "upcoming") -> list[dict]:
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM races WHERE status = ? ORDER BY date ASC", (status,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_race_status(race_id: int, status: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE races SET status = ? WHERE id = ?", (status, race_id))
