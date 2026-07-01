from pathlib import Path
from app import config


def test_paths_are_under_project_root():
    assert config.PROBLEMS_DIR == config.ROOT / "problems"
    assert config.DATA_DIR == config.ROOT / "data"
    assert config.SESSIONS_DIR == config.DATA_DIR / "sessions"
    assert config.SCHEDULE_PATH == config.DATA_DIR / "schedule.json"
    assert config.FRONTEND_DIR == config.ROOT / "app" / "frontend"


def test_default_config_has_required_keys():
    c = config.DEFAULT_CONFIG
    assert c["daily_new"] >= 1
    assert c["starting_ease"] == 2.5
    assert "target_minutes" in c and "Medium" in c["target_minutes"]
    assert isinstance(c["weak_concept_bias"], bool)


def test_ensure_dirs_creates_data_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(config, "SESSIONS_DIR", tmp_path / "data" / "sessions")
    config.ensure_dirs()
    assert (tmp_path / "data" / "sessions").is_dir()
