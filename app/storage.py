from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
from app.models import Problem
from app.scheduler import quality_from_level, PASS_LEVELS, update_sm2, update_concepts

_EMPTY_SCHEDULE = {"problems": {}, "concepts": {}}


def load_problems(problems_dir: Path) -> dict[str, Problem]:
    out: dict[str, Problem] = {}
    for path in sorted(Path(problems_dir).glob("*.json")):
        p = Problem.from_file(path)
        out[p.slug] = p
    return out


def load_schedule(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "problems" not in data:
            return {"problems": {}, "concepts": {}}
        data.setdefault("concepts", {})
        return data
    except (FileNotFoundError, ValueError):
        return {"problems": {}, "concepts": {}}


def save_schedule(path: Path, schedule: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(schedule, f, indent=2)
    os.replace(tmp, path)


def load_config(path: Path, defaults: dict) -> dict:
    merged = dict(defaults)
    try:
        merged.update(json.loads(Path(path).read_text(encoding="utf-8")))
    except (FileNotFoundError, ValueError):
        pass
    return merged


def append_session(sessions_dir: Path, session: dict) -> Path:
    sessions_dir = Path(sessions_dir)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{session['timestamp']}-{session['slug']}"
    path = sessions_dir / f"{stem}.json"
    n = 2
    while path.exists():
        path = sessions_dir / f"{stem}-{n}.json"
        n += 1
    path.write_text(json.dumps(session, indent=2), encoding="utf-8")
    return path


def load_sessions(sessions_dir: Path) -> list[dict]:
    """Load all attempt-log JSONs from data/sessions/ (empty list if missing/corrupt)."""
    out = []
    for path in sorted(Path(sessions_dir).glob("*.json")):
        try:
            out.append(json.loads(path.read_text(encoding="utf-8")))
        except (ValueError, OSError):
            continue
    return out


def record_attempt(schedule: dict, slug: str, problem: Problem, level: str,
                   today: str, config: dict) -> dict:
    problems = {k: dict(v) for k, v in schedule.get("problems", {}).items()}
    quality = quality_from_level(level)
    state = problems.get(slug, {"ease": config["starting_ease"], "interval": 0,
                                "repetitions": 0, "due": None, "last_result": None})
    new_state = update_sm2(state, quality, today, config["initial_intervals"])
    new_state["last_result"] = level
    problems[slug] = new_state
    concepts = update_concepts(schedule.get("concepts", {}), problem.concepts,
                               clean=(level in PASS_LEVELS))
    return {"problems": problems, "concepts": concepts}
