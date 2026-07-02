import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    from app import config, storage
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(config, "SESSIONS_DIR", tmp_path / "data" / "sessions")
    monkeypatch.setattr(config, "SCHEDULE_PATH", tmp_path / "data" / "schedule.json")
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "data" / "config.json")
    import app.main as main
    monkeypatch.setattr(main, "_today", lambda: "2026-07-01")
    monkeypatch.setattr(main, "_now_iso", lambda: "2026-07-01T09-00-00")
    return TestClient(main.app)


def test_list_problems(client):
    r = client.get("/api/problems")
    assert r.status_code == 200
    body = r.json()
    slugs = [p["slug"] for p in body]
    assert "two-sum" in slugs
    for p in body:
        assert "last_result" in p
        assert "repetitions" in p
        assert p["last_result"] is None
        assert p["repetitions"] == 0


def test_list_problems_reflects_last_attempt(client):
    client.post("/api/attempt", json={
        "slug": "two-sum", "code": "x=1", "elapsed_ms": 300000,
        "result": "good", "notes": {},
    })
    r = client.get("/api/problems")
    two = next(p for p in r.json() if p["slug"] == "two-sum")
    assert two["last_result"] == "good"
    assert two["repetitions"] == 1


def test_get_problem(client):
    r = client.get("/api/problem/two-sum")
    assert r.json()["entry_point"] == "two_sum"


def test_run_endpoint(client):
    r = client.post("/api/run", json={"code": "print(2+2)"})
    assert r.json()["stdout"].strip() == "4"


def test_submit_correct_solution(client):
    code = "def two_sum(nums, target):\n    seen={}\n    for j,x in enumerate(nums):\n        if target-x in seen: return [seen[target-x],j]\n        seen[x]=j\n"
    r = client.post("/api/submit", json={"slug": "two-sum", "code": code})
    assert r.json()["all_passed"] is True


def test_attempt_persists_and_returns_next(client):
    r = client.post("/api/attempt", json={
        "slug": "two-sum", "code": "x=1", "elapsed_ms": 300000,
        "result": "good", "notes": {"restate": "find two indices"},
    })
    body = r.json()
    assert body["schedule_state"]["repetitions"] == 1
    assert "next" in body
    # persisted: listing now shows two-sum as seen
    r2 = client.get("/api/problems")
    two = next(p for p in r2.json() if p["slug"] == "two-sum")
    assert two["seen"] is True


def test_attempt_persists_test_summary(client):
    from app import config
    import json

    r = client.post("/api/attempt", json={
        "slug": "two-sum", "code": "x=1", "elapsed_ms": 300000,
        "result": "easy", "notes": {},
        "test_summary": {"passed": 3, "total": 3, "all_passed": True},
    })
    assert r.status_code == 200
    session_files = list(config.SESSIONS_DIR.glob("*.json"))
    assert len(session_files) == 1
    saved = json.loads(session_files[0].read_text(encoding="utf-8"))
    assert saved["test_summary"] == {"passed": 3, "total": 3, "all_passed": True}


def test_attempt_invalid_level_returns_422(client):
    r = client.post("/api/attempt", json={
        "slug": "two-sum", "code": "x=1", "elapsed_ms": 300000,
        "result": "clean", "notes": {},
    })
    assert r.status_code == 422


def test_next_endpoint(client):
    assert client.get("/api/next").json()["reason"] in {"review", "new", "done"}


def test_problems_include_track(client):
    items = client.get("/api/problems").json()
    assert all("track" in it for it in items)


def test_next_track_filter(client):
    # with no ML problems seeded in the fixture, ml track → nothing recommended
    out = client.get("/api/next?track=ml").json()
    assert out["reason"] in {"new", "review", "done"}


def test_next_empty_track_behaves_like_all(client):
    # An empty track query param (as sent by the frontend's default "All" deck)
    # must behave the same as omitting the param entirely.
    empty = client.get("/api/next?track=").json()
    all_ = client.get("/api/next").json()
    assert empty["recommended"] is not None
    assert empty["recommended"] == all_["recommended"]
    assert empty["reason"] == "new"


def test_get_config_returns_defaults(client):
    r = client.get("/api/config")
    assert r.status_code == 200
    cfg = r.json()
    assert cfg["starting_ease"] == 2.5
    assert cfg["daily_new"] == 2
    assert "target_minutes" in cfg


def test_focus_groups_endpoint(client):
    ids = {g["id"] for g in client.get("/api/focus-groups").json()}
    assert "ml-attention" in ids and "coding-dp" in ids


def test_next_focus_scopes_to_group(client):
    # coding-dp focus -> recommended problem (if any) is a dp coding problem or 'done'
    out = client.get("/api/next?focus=coding-dp").json()
    assert out["reason"] in {"new", "review", "done"}
    if out["recommended"]:
        p = client.get("/api/problem/" + out["recommended"]).json()
        assert p["track"] == "coding" and "dynamic-programming" in p["concepts"]


def test_problems_focus_filter(client):
    items = client.get("/api/problems?focus=coding").json()
    assert items and all(it["track"] == "coding" for it in items)


def test_post_config_persists_merge(client):
    from app import config
    # POST with {"daily_new": 5}
    r = client.post("/api/config", json={"daily_new": 5})
    assert r.status_code == 200
    merged = r.json()
    assert merged["daily_new"] == 5
    assert merged["starting_ease"] == 2.5  # default still present
    # Verify GET returns the persisted value
    r2 = client.get("/api/config")
    assert r2.json()["daily_new"] == 5
    # Verify the file was written to CONFIG_PATH
    assert config.CONFIG_PATH.exists()
    import json
    saved = json.loads(config.CONFIG_PATH.read_text(encoding="utf-8"))
    assert saved["daily_new"] == 5
