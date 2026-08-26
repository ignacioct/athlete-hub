#!/usr/bin/env python3
"""One-time bulk import from config/races.yaml. See that file for the format."""

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.races import add_race  # noqa: E402


def main():
    config_path = Path(__file__).resolve().parent.parent / "config" / "races.yaml"
    data = yaml.safe_load(config_path.read_text())

    for race in data.get("races", []):
        race_id = add_race(
            name=race["name"],
            race_date=race["date"],
            distance_km=race.get("distance_km"),
            priority=race.get("priority", "B"),
            goal_time=race.get("goal_time"),
            notes=race.get("notes", ""),
        )
        print(f"Added race #{race_id}: {race['name']} ({race['date']})")


if __name__ == "__main__":
    main()
