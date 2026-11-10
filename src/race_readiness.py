"""
Race readiness for the "Race build" panel, measured against the season's own
training plan (data/training_plan.json, copied from Notion) instead of a
generic distance rule of thumb.

Each race owns the plan weeks between the previous race and itself (its
block). Every race shows its block's planned peak week; the race whose block
you're in also shows plan compliance: the last 2 full weeks' actual km vs.
planned km, plus this week so far.
"""

import json
from datetime import date, timedelta
from pathlib import Path

from src.activities import get_deduped_activities

PLAN_PATH = Path(__file__).resolve().parent.parent / "data" / "training_plan.json"
COMPLIANCE_WEEKS = 2


def load_plan() -> dict:
    return json.loads(PLAN_PATH.read_text())["weeks"]


def _week_km(conn, monday: date) -> float:
    rows = get_deduped_activities(
        conn, monday.isoformat(), (monday + timedelta(weeks=1)).isoformat(), sport_like="run"
    )
    return round(sum((r["distance_m"] or 0) for r in rows) / 1000, 1)


def race_readiness(conn, race: dict, block_start: str | None, plan: dict, today: date | None = None) -> dict:
    """`block_start` is the previous race's date (None for the first race);
    the race's block is the plan weeks after it and before this race."""
    today = today or date.today()
    block = {w: p for w, p in plan.items() if (block_start is None or w > block_start) and w < race["date"]}
    result = {"plan_peak_km": max((p["km"] for p in block.values()), default=None)}

    in_block = (block_start is None or today.isoformat() > block_start) and today.isoformat() <= race["date"]
    if not block or not in_block:
        return result

    monday = today - timedelta(days=today.weekday())
    past = [monday - timedelta(weeks=i) for i in range(COMPLIANCE_WEEKS, 0, -1)]
    planned = [plan.get(m.isoformat(), {}).get("km") for m in past]
    if None not in planned:
        actual_avg = round(sum(_week_km(conn, m) for m in past) / COMPLIANCE_WEEKS, 1)
        planned_avg = round(sum(planned) / COMPLIANCE_WEEKS, 1)
        result |= {
            "actual_avg_km": actual_avg,
            "planned_avg_km": planned_avg,
            "pct_of_plan": round(min(150, actual_avg / planned_avg * 100)),
        }

    this_week = plan.get(monday.isoformat())
    if this_week:
        result |= {"week_km": _week_km(conn, monday), "week_planned_km": this_week["km"]}
    return result
