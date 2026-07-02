from __future__ import annotations
from datetime import datetime
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app import config, storage, executor, scheduler
from app.focus import get_group, matches, group_list as focus_group_list

app = FastAPI(title="reps")


def _today() -> str:
    return datetime.now().date().isoformat()


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


def _problems() -> dict:
    return storage.load_problems(config.PROBLEMS_DIR)


def _config() -> dict:
    return storage.load_config(config.CONFIG_PATH, config.DEFAULT_CONFIG)


class RunBody(BaseModel):
    code: str


class SubmitBody(BaseModel):
    slug: str
    code: str


class AttemptBody(BaseModel):
    slug: str
    code: str
    elapsed_ms: int
    result: Literal["easy", "good", "hard", "hint", "peeked"]
    notes: dict = {}
    test_summary: dict | None = None
    track: str | None = None
    focus: str | None = None


@app.get("/api/focus-groups")
def focus_groups():
    return focus_group_list()


@app.get("/api/problems")
def list_problems(focus: str | None = None):
    schedule = storage.load_schedule(config.SCHEDULE_PATH)
    seen = schedule["problems"]
    group = get_group(focus)
    out = []
    for slug, p in _problems().items():
        st = seen.get(slug)
        item = {"slug": slug, "title": p.title, "difficulty": p.difficulty,
                "concepts": p.concepts, "seen": st is not None,
                "due": st.get("due") if st else None,
                "last_result": st.get("last_result") if st else None,
                "repetitions": st.get("repetitions", 0) if st else 0,
                "track": p.track, "libraries": p.libraries, "source": p.source}
        if matches(item, group):
            out.append(item)
    return out


@app.get("/api/problem/{slug}")
def get_problem(slug: str):
    p = _problems().get(slug)
    if not p:
        raise HTTPException(404, f"No problem {slug!r}")
    return p.model_dump()


@app.post("/api/run")
def run_code(body: RunBody):
    return executor.run(body.code)


@app.post("/api/submit")
def submit(body: SubmitBody):
    p = _problems().get(body.slug)
    if not p:
        raise HTTPException(404, f"No problem {body.slug!r}")
    rt = p.random_tests
    if p.reference and rt and rt.get("mode") == "autograd":
        result = executor.run_autograd_tests(body.code, p.entry_point, p.reference, rt,
                                             rtol=p.rtol, atol=p.atol)
    elif p.reference and rt:
        result = executor.run_reference_tests(body.code, p.entry_point, p.reference, rt,
                                              p.compare, p.libraries, rtol=p.rtol, atol=p.atol,
                                              banned=p.banned)
    else:
        result = executor.run_tests(body.code, p.entry_point, [t.model_dump() for t in p.tests],
                                    p.compare, rtol=p.rtol, atol=p.atol, banned=p.banned)
    return result


@app.post("/api/attempt")
def attempt(body: AttemptBody):
    problems = _problems()
    p = problems.get(body.slug)
    if not p:
        raise HTTPException(404, f"No problem {body.slug!r}")
    cfg = _config()
    today = _today()
    schedule = storage.load_schedule(config.SCHEDULE_PATH)
    schedule = storage.record_attempt(schedule, body.slug, p, body.result, today, cfg)
    storage.save_schedule(config.SCHEDULE_PATH, schedule)
    storage.append_session(config.SESSIONS_DIR, {
        "timestamp": _now_iso(), "slug": body.slug, "result": body.result,
        "elapsed_ms": body.elapsed_ms, "code": body.code, "notes": body.notes,
        "test_summary": body.test_summary,
    })
    prob_dicts = [{"slug": s, "difficulty": pr.difficulty, "concepts": pr.concepts, "track": pr.track,
                   "libraries": pr.libraries, "source": pr.source}
                  for s, pr in problems.items()]
    focus_group = get_group(body.focus)
    if body.focus:
        filtered = [pd for pd in prob_dicts if matches(pd, focus_group)]
        nxt = scheduler.recommend_next(filtered, schedule, today, cfg)
    else:
        nxt = scheduler.recommend_next(prob_dicts, schedule, today, cfg, track=(body.track or None))
    return {"schedule_state": schedule["problems"][body.slug], "next": nxt}


@app.get("/api/next")
def next_problem(track: str | None = None, focus: str | None = None):
    track = track or None
    focus = focus or None
    problems = _problems()
    schedule = storage.load_schedule(config.SCHEDULE_PATH)
    prob_dicts = [{"slug": s, "difficulty": p.difficulty, "concepts": p.concepts, "track": p.track,
                   "libraries": p.libraries, "source": p.source}
                  for s, p in problems.items()]
    if focus is not None:
        group = get_group(focus)
        filtered = [p for p in prob_dicts if matches(p, group)]
        return scheduler.recommend_next(filtered, schedule, _today(), _config())
    return scheduler.recommend_next(prob_dicts, schedule, _today(), _config(), track=track)


@app.get("/api/config")
def get_config():
    return _config()


@app.post("/api/config")
def set_config(new: dict):
    cfg = _config()
    cfg.update(new)
    storage.save_schedule(config.CONFIG_PATH, cfg)  # reuse atomic writer
    return cfg


# Static frontend at "/" (mounted last so /api/* wins).
if config.FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(config.FRONTEND_DIR), html=True), name="frontend")
