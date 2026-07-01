from app.scheduler import quality_from_result, update_sm2, update_concepts, concept_rate, recommend_next

INTERVALS = [1, 3, 7]

CONFIG = {"weak_concept_bias": True, "daily_new": 2}

PROBLEMS = [
    {"slug": "two-sum", "difficulty": "Easy", "concepts": ["hashing"]},
    {"slug": "coin-change", "difficulty": "Medium", "concepts": ["dp"]},
    {"slug": "num-islands", "difficulty": "Medium", "concepts": ["graphs"]},
]


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


def test_update_concepts_counts_attempts_and_cleans():
    m = update_concepts({}, ["hashing", "arrays"], clean=True)
    assert m["hashing"] == {"attempts": 1, "cleans": 1}
    m = update_concepts(m, ["hashing"], clean=False)
    assert m["hashing"] == {"attempts": 2, "cleans": 1}


def test_concept_rate_unseen_is_zero():
    assert concept_rate({}, "dp") == 0.0
    assert concept_rate({"dp": {"attempts": 2, "cleans": 1}}, "dp") == 0.5


def test_recommend_returns_overdue_review_first():
    schedule = {"problems": {"two-sum": {"due": "2026-06-01"}}, "concepts": {}}
    out = recommend_next(PROBLEMS, schedule, "2026-07-01", CONFIG)
    assert out["recommended"] == "two-sum"
    assert out["reason"] == "review"
    assert "two-sum" in out["due"]


def test_recommend_picks_new_from_weakest_concept():
    # dp mastery is terrible, graphs is fine -> coin-change (dp) should win.
    schedule = {
        "problems": {},
        "concepts": {"dp": {"attempts": 4, "cleans": 0},
                     "graphs": {"attempts": 4, "cleans": 4}},
    }
    out = recommend_next(PROBLEMS, schedule, "2026-07-01", CONFIG)
    assert out["recommended"] == "coin-change"
    assert out["reason"] == "new"


def test_recommend_done_when_all_seen_and_not_due():
    schedule = {"problems": {p["slug"]: {"due": "2026-08-01"} for p in PROBLEMS}, "concepts": {}}
    out = recommend_next(PROBLEMS, schedule, "2026-07-01", CONFIG)
    assert out["recommended"] is None
    assert out["reason"] == "done"
