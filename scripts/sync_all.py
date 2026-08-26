#!/usr/bin/env python3
"""
Runs every sync in order. On-demand, not cron-scheduled — the sync machine
isn't guaranteed to be on, so this is triggered instead by the dashboard's
"Sync now" button (dashboard/server.py's POST /api/sync) or by asking Claude
to sync (mcp_server/server.py's sync_now tool). Both call main() below.

    python scripts/sync_all.py --days 7

--days controls the Garmin/intervals.icu lookback window. Garmin's sync logs
in via Selenium on every run, so a routine sync should use a short window (7
days is plenty of overlap) rather than the 90-day default meant for
first-time/manual backfills.
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard import generate_data  # noqa: E402
from src import garmin_sync, hevy_sync, intervals_sync  # noqa: E402


def main(days_back: int = 90) -> dict:
    started = time.time()
    results = {}

    for label, fn in [
        ("hevy", hevy_sync.sync),
        ("intervals.icu", lambda: intervals_sync.pull_to_db(days_back)),
        ("garmin", lambda: garmin_sync.sync(days_back)),
    ]:
        print(f"--- syncing {label} ---")
        try:
            results[label] = fn()
            print(f"{label}: OK -> {results[label]}")
        except Exception as e:
            results[label] = f"FAILED: {e}"
            print(f"{label}: FAILED -> {e}", file=sys.stderr)

    print("--- regenerating dashboard data.json ---")
    try:
        generate_data.main()
    except Exception as e:
        print(f"dashboard data generation FAILED -> {e}", file=sys.stderr)

    print(f"\nDone in {time.time() - started:.1f}s")
    print(results)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=90, help="lookback window for Garmin/intervals.icu (default 90; use a small window for routine on-demand syncs)")
    args = parser.parse_args()
    main(args.days)
