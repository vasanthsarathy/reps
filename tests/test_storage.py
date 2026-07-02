import json
from app import storage
from app.models import Problem
from app import config


def test_load_problems_reads_two_sum():
    problems = storage.load_problems(config.PROBLEMS_DIR)
    assert "two-sum" in problems
    assert isinstance(problems["two-sum"], Problem)


def test_load_schedule_missing_returns_empty(tmp_path):
    s = storage.load_schedule(tmp_path / "nope.json")
    assert s == {"problems": {}, "concepts": {}}


def test_load_schedule_corrupt_returns_empty(tmp_path):
    p = tmp_path / "schedule.json"
    p.write_text("{ this is not json", encoding="utf-8")
    assert storage.load_schedule(p) == {"problems": {}, "concepts": {}}


def test_save_then_load_schedule_roundtrips(tmp_path):
    p = tmp_path / "sched.json"
    data = {"problems": {"two-sum": {"ease": 2.6}}, "concepts": {"hashing": {"attempts": 1, "cleans": 1}}}
    storage.save_schedule(p, data)
    assert storage.load_schedule(p) == data


def test_load_config_merges_defaults(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"daily_new": 5}), encoding="utf-8")
    cfg = storage.load_config(p, config.DEFAULT_CONFIG)
    assert cfg["daily_new"] == 5
    assert cfg["starting_ease"] == 2.5  # merged from defaults


def test_append_session_writes_file(tmp_path):
    path = storage.append_session(tmp_path, {"timestamp": "2026-07-01T09-00-00", "slug": "two-sum", "result": "clean"})
    assert path.exists()
    assert json.loads(path.read_text())["result"] == "clean"


def test_append_session_collision_writes_distinct_files(tmp_path):
    session = {"timestamp": "2026-07-01T09-00-00", "slug": "two-sum", "result": "clean"}
    path1 = storage.append_session(tmp_path, session)
    path2 = storage.append_session(tmp_path, session)
    assert path1.exists()
    assert path2.exists()
    assert path1 != path2


def test_record_attempt_updates_schedule_and_concepts():
    problems = storage.load_problems(config.PROBLEMS_DIR)
    p = problems["two-sum"]
    schedule = {"problems": {}, "concepts": {}}
    out = storage.record_attempt(schedule, "two-sum", p, "good",
                                 "2026-07-01", config.DEFAULT_CONFIG)
    assert out["problems"]["two-sum"]["repetitions"] == 1
    assert out["concepts"]["hashing"] == {"attempts": 1, "cleans": 1}
    # original not mutated
    assert schedule["problems"] == {}


def test_record_attempt_miss_does_not_count_as_clean():
    problems = storage.load_problems(config.PROBLEMS_DIR)
    p = problems["two-sum"]
    schedule = {"problems": {}, "concepts": {}}
    out = storage.record_attempt(schedule, "two-sum", p, "peeked",
                                 "2026-07-01", config.DEFAULT_CONFIG)
    assert out["concepts"]["hashing"] == {"attempts": 1, "cleans": 0}
