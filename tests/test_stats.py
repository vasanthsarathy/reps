from app.models import Problem
from app.stats import compute_stats


def _p(slug, track="coding"):
    return Problem(slug=slug, title=slug, difficulty="Easy", concepts=[], source="x",
                   description="", entry_point="f", starter_code="def f(): pass", track=track)


def test_compute_stats_counts_and_stages():
    problems = {"a": _p("a"), "b": _p("b"), "c": _p("c", "ml")}
    schedule = {"problems": {
                    "a": {"repetitions": 1, "due": "2026-06-01", "last_result": "good"},
                    "c": {"repetitions": 4, "due": "2026-08-01", "last_result": "easy"}},
                "concepts": {"dp": {"attempts": 4, "cleans": 1}, "graphs": {"attempts": 2, "cleans": 2}}}
    out = compute_stats(problems, schedule, "2026-07-01", [])
    assert out["overall"] == {"total": 3, "attempted": 2, "due": 1}
    assert out["by_track"]["ml"] == {"total": 1, "attempted": 1, "due": 0}
    assert out["stages"] == {"new": 1, "learning": 1, "reviewing": 1}
    assert out["ratings"] == {"good": 1, "easy": 1}
    # weakest concept first (dp 0.25 before graphs 1.0)
    assert [r["tag"] for r in out["concepts"]] == ["dp", "graphs"]
    assert out["concepts"][0]["rate"] == 0.25


def test_compute_stats_recent_sorted():
    out = compute_stats({}, {"problems": {}, "concepts": {}}, "2026-07-01",
                        [{"slug": "a", "result": "good", "timestamp": "2026-07-01T09-00-00"},
                         {"slug": "b", "result": "hard", "timestamp": "2026-07-01T10-00-00"}])
    assert [r["slug"] for r in out["recent"]] == ["b", "a"]
