from app.scheduler import quality_from_result, update_sm2

INTERVALS = [1, 3, 7]


def test_quality_clean_fast_is_5():
    assert quality_from_result("clean", 10 * 60_000, 20 * 60_000) == 5


def test_quality_clean_slow_is_4():
    assert quality_from_result("clean", 25 * 60_000, 20 * 60_000) == 4


def test_quality_peeked_is_2():
    assert quality_from_result("peeked", 5 * 60_000, 20 * 60_000) == 2


def test_quality_failed_is_1():
    assert quality_from_result("failed", 5 * 60_000, 20 * 60_000) == 1


def _fresh():
    return {"ease": 2.5, "interval": 0, "repetitions": 0, "due": None, "last_result": None}


def test_first_clean_uses_first_interval():
    s = update_sm2(_fresh(), 5, "2026-07-01", INTERVALS)
    assert s["repetitions"] == 1
    assert s["interval"] == 1
    assert s["due"] == "2026-07-02"
    assert s["ease"] > 2.5  # quality 5 raises ease


def test_second_clean_uses_second_interval():
    s = update_sm2(_fresh(), 5, "2026-07-01", INTERVALS)
    s = update_sm2(s, 5, "2026-07-02", INTERVALS)
    assert s["repetitions"] == 2
    assert s["interval"] == 3
    assert s["due"] == "2026-07-05"


def test_fourth_rep_multiplies_by_ease():
    s = _fresh()
    for day in ("2026-07-01", "2026-07-02", "2026-07-05", "2026-07-12"):
        s = update_sm2(s, 5, day, INTERVALS)
    assert s["repetitions"] == 4
    assert s["interval"] == round(7 * s["ease"])


def test_low_quality_resets_repetitions():
    s = update_sm2(_fresh(), 5, "2026-07-01", INTERVALS)
    s = update_sm2(s, 5, "2026-07-02", INTERVALS)
    s = update_sm2(s, 2, "2026-07-05", INTERVALS)  # peeked
    assert s["repetitions"] == 0
    assert s["interval"] == 1
    assert s["due"] == "2026-07-06"


def test_ease_floored_at_1_3():
    s = _fresh()
    for _ in range(6):
        s = update_sm2(s, 1, "2026-07-01", INTERVALS)
    assert s["ease"] >= 1.3
