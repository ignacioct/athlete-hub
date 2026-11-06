"""Run with: uv run python -m tests.test_activities"""

import sqlite3

from src.activities import _COLUMNS, get_deduped_activities


def test_excluded_treadmill_walk_is_not_returned():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(f"CREATE TABLE activities ({_COLUMNS}, is_strength_duplicate INTEGER DEFAULT 0)")
    conn.executemany(
        "INSERT INTO activities (id, source, sport, start_time_utc, distance_m) VALUES (?, ?, ?, ?, ?)",
        [
            ("intervals:i202887550", "intervals", "VirtualRun", "2026-10-28T17:45:47", 1900),
            ("garmin:24884926681", "garmin", "treadmill_running", "2026-10-28T17:45:47", 1900),
            ("intervals:real-run", "intervals", "Run", "2026-10-29T17:22:51", 9012),
        ],
    )

    rows = get_deduped_activities(conn, "2026-10-26", sport_like="run")

    assert [r["id"] for r in rows] == ["intervals:real-run"]


if __name__ == "__main__":
    test_excluded_treadmill_walk_is_not_returned()
    print("ok")
