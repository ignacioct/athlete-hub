#!/usr/bin/env python3
"""
Runs every sync in order. Safe to schedule via cron/launchd/systemd:

    0 6,20 * * * cd /path/to/athlete-hub && .venv/bin/python scripts/sync_all.py >> sync.log 2>&1
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard import generate_data  # noqa: E402
from src import garmin_sync, hevy_sync, intervals_sync  # noqa: E402


def main() -> None:
    started = time.time()
    results = {}

    for label, fn in [
        ("hevy", hevy_sync.sync),
        ("intervals.icu", intervals_sync.pull_to_db),
        ("garmin", garmin_sync.sync),
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


if __name__ == "__main__":
    main()
