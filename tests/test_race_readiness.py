"""Run with: uv run python -m tests.test_race_readiness"""

import sqlite3
from datetime import date

from src.activities import _COLUMNS
from src.race_readiness import race_readiness

PLAN = {
    "2026-10-26": {"km": 42},
    "2026-11-02": {"km": 45},
    "2026-11-09": {"km": 45, "long": 12},
    "2026-11-16": {"km": 24},
    "2026-11-30": {"km": 40},
}


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(f"CREATE TABLE activities ({_COLUMNS}, is_strength_duplicate INTEGER DEFAULT 0)")
    conn.executemany(
        "INSERT INTO activities (id, source, sport, start_time_utc, distance_m) VALUES (?, ?, ?, ?, ?)",
        [
            ("a", "intervals", "Run", "2026-10-28T08:00:00", 42000),
            ("b", "intervals", "Run", "2026-11-04T08:00:00", 45000),
            ("c", "intervals", "Run", "2026-11-09T08:00:00", 12000),
        ],
    )
    return conn


def test_active_block_compares_against_plan():
    r = race_readiness(_conn(), {"date": "2026-11-22"}, "2026-10-04", PLAN, today=date(2026, 11, 10))
    assert r == {
        "plan_peak_km": 45, "actual_avg_km": 43.5, "planned_avg_km": 43.5,
        "pct_of_plan": 100, "week_km": 12.0, "week_planned_km": 45,
    }


def test_future_block_shows_peak_only_and_unplanned_race_has_none():
    conn = _conn()
    today = date(2026, 11, 10)
    assert race_readiness(conn, {"date": "2026-12-31"}, "2026-11-22", PLAN, today=today) == {"plan_peak_km": 40}
    assert race_readiness(conn, {"date": "2027-04-25"}, "2027-02-14", PLAN, today=today) == {"plan_peak_km": None}


if __name__ == "__main__":
    test_active_block_compares_against_plan()
    test_future_block_shows_peak_only_and_unplanned_race_has_none()
    print("ok")
