from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBLEMS_DIR = ROOT / "problems"
DATA_DIR = ROOT / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
SCHEDULE_PATH = DATA_DIR / "schedule.json"
CONFIG_PATH = DATA_DIR / "config.json"
FRONTEND_DIR = ROOT / "app" / "frontend"

DEFAULT_CONFIG = {
    "daily_new": 2,
    "starting_ease": 2.5,
    "initial_intervals": [1, 3, 7],  # days for reps 1, 2, 3 before SM-2 takes over
    "weak_concept_bias": True,
    "target_minutes": {"Easy": 10, "Medium": 20, "Hard": 35},
}


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
