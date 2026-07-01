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
