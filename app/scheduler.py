from __future__ import annotations
from datetime import date, timedelta

_RESULT_QUALITY = {"peeked": 2, "failed": 1}


def quality_from_result(result: str, elapsed_ms: int, target_ms: int) -> int:
    if result == "clean":
        return 5 if elapsed_ms <= target_ms else 4
    return _RESULT_QUALITY.get(result, 1)


def _iso_plus_days(today: str, days: int) -> str:
    return (date.fromisoformat(today) + timedelta(days=days)).isoformat()


def update_sm2(state: dict, quality: int, today: str, intervals: list[int]) -> dict:
    ease = state.get("ease", 2.5)
    reps = state.get("repetitions", 0)
    interval = state.get("interval", 0)

    # SM-2 ease update, floored at 1.3.
    ease = max(1.3, ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))

    if quality < 3:
        reps = 0
        interval = 1
    else:
        reps += 1
        if reps <= len(intervals):
            interval = intervals[reps - 1]
        else:
            interval = max(1, round(interval * ease))

    return {
        "ease": round(ease, 4),
        "interval": interval,
        "repetitions": reps,
        "due": _iso_plus_days(today, interval),
        "last_result": state.get("last_result"),
    }


def update_concepts(mastery: dict, concepts: list[str], clean: bool) -> dict:
    out = {k: dict(v) for k, v in mastery.items()}
    for tag in concepts:
        row = out.setdefault(tag, {"attempts": 0, "cleans": 0})
        row["attempts"] += 1
        if clean:
            row["cleans"] += 1
    return out


def concept_rate(mastery: dict, tag: str) -> float:
    row = mastery.get(tag)
    if not row or row["attempts"] == 0:
        return 0.0
    return row["cleans"] / row["attempts"]


def recommend_next(problems: list[dict], schedule: dict, today: str, config: dict) -> dict:
    sched_problems = schedule.get("problems", {})
    mastery = schedule.get("concepts", {})

    due = sorted(
        (slug for slug, st in sched_problems.items() if st.get("due") and st["due"] <= today),
        key=lambda s: sched_problems[s]["due"],
    )
    stats = {"total": len(problems), "seen": len(sched_problems), "due_count": len(due)}

    if due:
        return {"recommended": due[0], "due": due, "reason": "review", "stats": stats}

    unseen = [p for p in problems if p["slug"] not in sched_problems]
    if not unseen:
        return {"recommended": None, "due": [], "reason": "done", "stats": stats}

    if config.get("weak_concept_bias", True):
        def weakness(p):
            min_rate = min((concept_rate(mastery, c) for c in p["concepts"]), default=0.0)
            unseen_count = sum(1 for c in p["concepts"] if c not in mastery)
            return (min_rate, unseen_count)
        unseen.sort(key=weakness)

    return {"recommended": unseen[0]["slug"], "due": [], "reason": "new", "stats": stats}
