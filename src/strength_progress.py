"""
Push/Pull/Legs weekly tracking, estimated 1RM progression for core lifts,
and recent PRs — shared by dashboard/generate_data.py and the MCP server's
get_strength_progress tool.

Session-level Push/Pull/Legs classification uses the workout's own title
rather than inferring from muscle groups: this account's 112 logged Hevy
sessions are titled "Push" (45x), "Pull" (44x), "Lower Body"/"Legs" (22x)
with near-total consistency — a far more reliable signal than trying to
bucket individual exercises by muscle group (RDL alone straddles hamstrings/
glutes/lower_back, which don't map cleanly to a single PPL category).

1RM is estimated via the Epley formula (weight * (1 + reps/30)) from each
session's best non-warmup set of a given exercise — Hevy computes its own
best_1rm PRs (visible in a set's prs_json) but only on sets that happen to
set a new record, not continuously, so it can't drive a progression chart
on its own.
"""

import json
from datetime import date, timedelta

CORE_LIFTS = [
    "Chest Press (Machine)",
    "Lat Pulldown (Cable)",
    "Seated Incline Curl (Dumbbell)",
    "Triceps Pushdown",
    "Squat (Barbell)",
    "Romanian Deadlift (Barbell)",
]


def _ppl_category(title: str | None) -> str | None:
    t = (title or "").lower()
    if "push" in t:
        return "Push"
    if "pull" in t:
        return "Pull"
    if "leg" in t or "lower" in t:
        return "Legs"
    return None


def weekly_split_status(conn, today: date) -> list[dict]:
    """Push/Pull/Legs done-or-not for the current week (Monday-Sunday)."""
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    sessions = conn.execute(
        """
        SELECT title, start_time_utc FROM strength_sessions
        WHERE date(start_time_utc) >= ? AND date(start_time_utc) <= ?
        ORDER BY start_time_utc ASC
        """,
        (monday.isoformat(), sunday.isoformat()),
    ).fetchall()

    done: dict[str, str] = {}
    for row in sessions:
        cat = _ppl_category(row["title"])
        if cat and cat not in done:
            done[cat] = row["start_time_utc"][:10]

    return [
        {"category": cat, "done": cat in done, "date": done.get(cat)}
        for cat in ("Push", "Pull", "Legs")
    ]


def _epley_1rm(weight_kg: float | None, reps: int | None) -> float | None:
    if weight_kg is None or not reps:
        return None
    return weight_kg * (1 + reps / 30)


def core_lift_1rm_history(conn, exercises: list[str] = CORE_LIFTS, days_back: int = 365) -> dict[str, list[dict]]:
    """Per exercise, one point per session: date + best estimated 1RM that
    session (max across its non-warmup sets)."""
    oldest = (date.today() - timedelta(days=days_back)).isoformat()
    result: dict[str, list[dict]] = {}

    for exercise in exercises:
        rows = conn.execute(
            """
            SELECT sess.start_time_utc AS ts, s.weight_kg, s.reps
            FROM strength_sets s
            JOIN strength_sessions sess ON sess.id = s.session_id
            WHERE s.exercise = ? AND s.set_type != 'warmup'
              AND date(sess.start_time_utc) >= ?
            ORDER BY sess.start_time_utc ASC
            """,
            (exercise, oldest),
        ).fetchall()

        by_session: dict[str, float] = {}
        for r in rows:
            est = _epley_1rm(r["weight_kg"], r["reps"])
            if est is None:
                continue
            d = r["ts"][:10]
            if est > by_session.get(d, 0):
                by_session[d] = est

        result[exercise] = [
            {"date": d, "est_1rm_kg": round(v, 1)} for d, v in sorted(by_session.items())
        ]

    return result


def recent_prs(conn, limit: int = 8) -> list[dict]:
    """Most recent Hevy-flagged PRs (best_weight / best_volume / best_1rm),
    newest first."""
    rows = conn.execute(
        """
        SELECT s.exercise, s.prs_json, sess.start_time_utc AS ts
        FROM strength_sets s
        JOIN strength_sessions sess ON sess.id = s.session_id
        WHERE s.prs_json IS NOT NULL
        ORDER BY sess.start_time_utc DESC
        LIMIT ?
        """,
        (limit * 3,),  # a session can have multiple PR'd sets; overfetch then trim
    ).fetchall()

    out = []
    for r in rows:
        for pr in json.loads(r["prs_json"]):
            value = pr.get("value")
            out.append({
                "exercise": r["exercise"],
                "date": r["ts"][:10],
                "type": pr.get("type"),
                "value": round(value, 1) if isinstance(value, float) else value,
            })
        if len(out) >= limit:
            break

    return out[:limit]
