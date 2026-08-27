"""
Rough race-readiness estimate for the "Upcoming races" panel: current
running volume vs. a peak-week target for that race, so "how ready am I"
and "what weekly km should I be hitting" have an actual number attached
instead of just a countdown.

This is a coaching rule-of-thumb, not a physiological model: peak-week
targets are drawn from widely-cited recreational-to-competitive running
guidance (Runner's World / RRCA-style bands: 5K ~16-40km/wk, 10K ~40-48,
half ~48-64, marathon ~48-97), picked toward the upper-middle of each band
for a competitive-recreational target rather than a beginner one. If that
doesn't match your own level, adjust PEAK_WEEKLY_KM_BY_DISTANCE below —
these are starting points, not a personalized model.

Distance alone isn't the whole story, though: how hard you should be
training for a given race depends on how much you're actually peaking for
it, which is exactly what this repo's existing A/B/C race priority field
already encodes (Joe Friel's standard race-priority framework — this isn't
a new concept invented for this feature, it's the same one the `priority`
column already models). So the distance-based target is scaled by
priority: A races (peak for this one) get the full target, B (train
through, race hard) gets 80%, C (tune-up) gets 60% — you're not supposed
to be specifically peaking for a tune-up race, so holding it to a full
peak-week target would be a false readout of "behind schedule."
"""

from datetime import date, timedelta

from src.activities import get_deduped_activities

# (min_km, max_km exclusive upper bound, priority-A peak weekly km)
PEAK_WEEKLY_KM_BY_DISTANCE = [
    (0, 6, 30),               # 5K-ish
    (6, 15, 45),              # 10K-ish
    (15, 25, 60),             # half-marathon-ish
    (25, float("inf"), 80),   # marathon-ish
]

PRIORITY_SCALE = {"A": 1.0, "B": 0.8, "C": 0.6}


def _peak_target_km(distance_km: float | None, priority: str) -> float | None:
    if distance_km is None:
        return None
    scale = PRIORITY_SCALE.get((priority or "B").upper(), PRIORITY_SCALE["B"])
    for lo, hi, base_target in PEAK_WEEKLY_KM_BY_DISTANCE:
        if lo <= distance_km < hi:
            return round(base_target * scale)
    return None


def _current_weekly_km(conn, weeks: int = 4) -> float:
    """Average running km/week over the trailing `weeks` full calendar
    weeks — deliberately excludes the current (possibly partial) week so a
    readiness check taken on a Tuesday doesn't look artificially low."""
    today = date.today()
    monday_this_week = today - timedelta(days=today.weekday())
    window_start = monday_this_week - timedelta(weeks=weeks)

    rows = get_deduped_activities(
        conn,
        window_start.isoformat(),
        monday_this_week.isoformat(),
        sport_like="run",
    )
    total_km = sum((r["distance_m"] or 0) for r in rows) / 1000
    return round(total_km / weeks, 1)


def race_readiness(conn, race: dict) -> dict | None:
    """Progress-toward-race estimate for one race row (as returned by
    src.races.list_races). Returns None when the race has no distance_km —
    there's no sane target to size without one."""
    target = _peak_target_km(race.get("distance_km"), race.get("priority"))
    if target is None:
        return None

    current = _current_weekly_km(conn)
    race_date = date.fromisoformat(race["date"])
    weeks_to_race = max(0, (race_date - date.today()).days // 7)
    pct_of_target = round(min(150, (current / target) * 100)) if target else None

    return {
        "current_weekly_km": current,
        "target_peak_weekly_km": target,
        "pct_of_target": pct_of_target,
        "weeks_to_race": weeks_to_race,
    }
