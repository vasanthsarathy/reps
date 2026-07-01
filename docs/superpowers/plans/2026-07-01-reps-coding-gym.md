# reps — Coding Interview Gym Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local three-column coding-interview gym for Blind 75 practice with live Python execution, syntax highlighting, an adjustable timer, R.E.P.S.-structured notes, and an SM-2 + concept-tag spaced-repetition engine that recommends the next problem.

**Architecture:** A thin FastAPI backend runs user Python in a subprocess (with a timeout), serves a static single-page frontend, and persists the problem library + user progress as plain files. Pure-logic modules (executor, scheduler, storage) are unit-tested with pytest; the frontend is verified manually. AI is deferred to Phase 2 but data is captured now.

**Tech Stack:** Python 3.14, uv (package/venv manager), FastAPI + uvicorn, pydantic v2, pytest + httpx (tests), CodeMirror via CDN (editor, no build step), vanilla HTML/CSS/JS frontend.

## Global Constraints

- Python `requires-python = ">=3.14"`; interpreter is provisioned by uv (`.python-version` = 3.14).
- All commands run through uv: `uv run <cmd>`. Never call `python`/`pip` directly (the bare `python` on this machine is a Microsoft Store stub).
- Dependencies already installed: `fastapi`, `uvicorn`, `pydantic` (runtime); `pytest`, `httpx` (dev). Add new deps only via `uv add`.
- Single user, localhost only. Bind server to `127.0.0.1`. No auth, no cloud.
- Executed user code is trusted (user's own machine); the only isolation is a subprocess + a hard timeout. Do NOT build a heavier sandbox.
- Problem descriptions and solution prose must be **original** — never copy LeetCode's wording.
- Scope is **Blind 75 only**. No NeetCode 150. No languages other than Python.
- `problems/` is version-controlled; `data/` (user state) is gitignored.
- Frontend loads libraries from CDN — no bundler/transpiler/node build step.
- Commit after every task with a `feat:`/`test:`/`chore:` message.

---

## File Structure

```
reps/
├── pyproject.toml              # uv-managed (exists)
├── .python-version             # 3.14 (exists)
├── uv.lock                     # (exists)
├── reps.py                     # launcher: start uvicorn + open browser (Task 12)
├── app/
│   ├── __init__.py             # (Task 1)
│   ├── config.py               # filesystem paths + scheduler defaults (Task 1)
│   ├── models.py               # Problem/TestCase/Solution/SM2State schemas (Task 2)
│   ├── executor.py             # run() + run_tests() via subprocess (Tasks 3-4)
│   ├── scheduler.py            # SM-2 + concept mastery + recommend_next (Tasks 5-6)
│   ├── storage.py              # load problems, schedule + session I/O (Task 7)
│   ├── main.py                 # FastAPI app + routes + static mount (Task 8)
│   └── frontend/
│       ├── index.html          # three-column layout (Task 9)
│       ├── style.css           # (Tasks 9-11)
│       └── app.js              # editor, run/submit, timer, notes, next (Tasks 9-11)
├── problems/
│   ├── two-sum.json            # seed fixture (Task 2), full set (Task 13)
│   └── ...
├── data/                       # gitignored; created at runtime
│   ├── config.json
│   ├── schedule.json
│   └── sessions/
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # shared fixtures (Task 2)
│   ├── test_models.py          # (Task 2)
│   ├── test_executor.py        # (Tasks 3-4)
│   ├── test_scheduler.py       # (Tasks 5-6)
│   ├── test_storage.py         # (Task 7)
│   ├── test_api.py             # (Task 8)
│   └── test_problems_valid.py  # every problem's reference solution passes its tests (Task 13)
└── docs/superpowers/{specs,plans}/
```

Root `main.py` from `uv init` is unused — delete it in Task 1.

---

### Task 1: Project skeleton + config

**Files:**
- Create: `app/__init__.py`, `app/config.py`, `tests/__init__.py`, `tests/test_config.py`
- Delete: `main.py` (default uv stub)

**Interfaces:**
- Produces: `app.config` module exposing `ROOT: Path`, `PROBLEMS_DIR: Path`, `DATA_DIR: Path`, `SESSIONS_DIR: Path`, `SCHEDULE_PATH: Path`, `CONFIG_PATH: Path`, `FRONTEND_DIR: Path`, and `DEFAULT_CONFIG: dict`; plus `ensure_dirs() -> None` that creates `DATA_DIR` and `SESSIONS_DIR` if missing.

- [ ] **Step 1: Write the failing test**

`tests/test_config.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: Create the package and config**

`app/__init__.py`:
```python
```
(empty file)

`tests/__init__.py`:
```python
```
(empty file)

`app/config.py`:
```python
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
```

- [ ] **Step 4: Delete the default stub**

```bash
rm main.py
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add app tests && git rm --cached main.py 2>/dev/null; rm -f main.py
git add -A
git commit -m "feat: add app package skeleton and config paths"
```

---

### Task 2: Problem schema, models, and a seed problem

**Files:**
- Create: `app/models.py`, `tests/conftest.py`, `tests/test_models.py`, `problems/two-sum.json`

**Interfaces:**
- Produces:
  - `TestCase(args: list, expected, )` pydantic model.
  - `Solution(name: str, explanation: str, code: str, complexity: str)`.
  - `Problem` pydantic model with fields: `slug: str`, `title: str`, `difficulty: str`, `concepts: list[str]`, `source: str`, `description: str`, `entry_point: str`, `starter_code: str`, `compare: str = "exact"` (`"exact"` or `"unordered"`), `tests: list[TestCase]`, `hints: list[str] = []`, `solutions: list[Solution] = []`.
  - `Problem.from_file(path: Path) -> Problem` classmethod.
- Consumes: nothing.

- [ ] **Step 1: Write the seed problem fixture**

`problems/two-sum.json`:
```json
{
  "slug": "two-sum",
  "title": "Two Sum",
  "difficulty": "Easy",
  "concepts": ["hashing", "arrays"],
  "source": "Blind75",
  "description": "You are given a list of integers `nums` and an integer `target`.\n\nReturn the indices of the two numbers that add up to `target`. Exactly one such pair exists, and you may not reuse the same index twice. Return them as a list `[i, j]` with `i < j`.\n\n**Example**\n\n```\nnums = [2, 7, 11, 15], target = 9  ->  [0, 1]   (2 + 7 = 9)\n```",
  "entry_point": "two_sum",
  "starter_code": "def two_sum(nums, target):\n    # Return [i, j] such that nums[i] + nums[j] == target.\n    pass\n",
  "compare": "exact",
  "tests": [
    {"args": [[2, 7, 11, 15], 9], "expected": [0, 1]},
    {"args": [[3, 2, 4], 6], "expected": [1, 2]},
    {"args": [[3, 3], 6], "expected": [0, 1]}
  ],
  "hints": [
    "Brute force is every pair — O(n^2). What would let you check 'have I seen the complement?' in O(1)?",
    "Walk left to right storing value -> index in a dict. For each x, look up target - x."
  ],
  "solutions": [
    {
      "name": "Hash map (one pass)",
      "explanation": "Scan once, keeping a dict of value -> index for everything seen so far. For each number x at index j, its partner must be target - x; if that partner is already in the dict at index i, then i < j and [i, j] is the answer. Storing after the lookup guarantees you never pair an element with itself.",
      "code": "def two_sum(nums, target):\n    seen = {}\n    for j, x in enumerate(nums):\n        if target - x in seen:\n            return [seen[target - x], j]\n        seen[x] = j\n    return []\n",
      "complexity": "Time O(n), Space O(n)"
    }
  ]
}
```

- [ ] **Step 2: Write the failing test**

`tests/conftest.py`:
```python
from pathlib import Path
import pytest
from app import config


@pytest.fixture
def two_sum_path() -> Path:
    return config.PROBLEMS_DIR / "two-sum.json"
```

`tests/test_models.py`:
```python
from app.models import Problem, TestCase, Solution


def test_load_two_sum_from_file(two_sum_path):
    p = Problem.from_file(two_sum_path)
    assert p.slug == "two-sum"
    assert p.entry_point == "two_sum"
    assert p.compare == "exact"
    assert "hashing" in p.concepts
    assert isinstance(p.tests[0], TestCase)
    assert p.tests[0].args == [[2, 7, 11, 15], 9]
    assert p.tests[0].expected == [0, 1]
    assert isinstance(p.solutions[0], Solution)
    assert p.solutions[0].name


def test_compare_defaults_to_exact():
    p = Problem(
        slug="x", title="X", difficulty="Easy", concepts=[], source="Blind75",
        description="", entry_point="f", starter_code="def f():\n    pass\n", tests=[],
    )
    assert p.compare == "exact"
    assert p.hints == []
    assert p.solutions == []
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models'`

- [ ] **Step 4: Implement models**

`app/models.py`:
```python
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field


class TestCase(BaseModel):
    args: list[Any]
    expected: Any


class Solution(BaseModel):
    name: str
    explanation: str
    code: str
    complexity: str = ""


class Problem(BaseModel):
    slug: str
    title: str
    difficulty: str
    concepts: list[str]
    source: str
    description: str
    entry_point: str
    starter_code: str
    compare: str = "exact"
    tests: list[TestCase] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    solutions: list[Solution] = Field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path) -> "Problem":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_models.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add app/models.py tests/conftest.py tests/test_models.py problems/two-sum.json
git commit -m "feat: add problem/models schema and two-sum seed problem"
```

---

### Task 3: Executor — run() scratchpad execution

**Files:**
- Create: `app/executor.py`, `tests/test_executor.py`

**Interfaces:**
- Produces: `run(code: str, timeout: float = 10.0) -> dict` with keys `stdout: str`, `stderr: str`, `error: str` (traceback text or `""`), `timed_out: bool`, `runtime_ms: int`.
- Consumes: nothing (uses `sys.executable` for the subprocess).

- [ ] **Step 1: Write the failing tests**

`tests/test_executor.py`:
```python
from app.executor import run


def test_run_captures_stdout():
    r = run("print('hello')")
    assert r["stdout"].strip() == "hello"
    assert r["error"] == ""
    assert r["timed_out"] is False


def test_run_captures_runtime_error_traceback():
    r = run("raise ValueError('boom')")
    assert "ValueError" in r["error"]
    assert "boom" in r["error"]


def test_run_times_out_on_infinite_loop():
    r = run("while True:\n    pass", timeout=1.0)
    assert r["timed_out"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_executor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.executor'`

- [ ] **Step 3: Implement run()**

`app/executor.py`:
```python
from __future__ import annotations
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def run(code: str, timeout: float = 10.0) -> dict:
    """Execute `code` as a standalone script in a subprocess; capture output."""
    with tempfile.TemporaryDirectory() as td:
        script = Path(td) / "user_code.py"
        script.write_text(code, encoding="utf-8")
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            return {
                "stdout": e.stdout or "", "stderr": e.stderr or "",
                "error": f"Timed out after {timeout:g}s",
                "timed_out": True,
                "runtime_ms": int((time.perf_counter() - start) * 1000),
            }
        runtime_ms = int((time.perf_counter() - start) * 1000)
        error = proc.stderr if proc.returncode != 0 else ""
        return {
            "stdout": proc.stdout, "stderr": proc.stderr, "error": error,
            "timed_out": False, "runtime_ms": runtime_ms,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_executor.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add app/executor.py tests/test_executor.py
git commit -m "feat: add executor.run for scratchpad code execution"
```

---

### Task 4: Executor — run_tests() against problem test cases

**Files:**
- Modify: `app/executor.py`
- Modify: `tests/test_executor.py`

**Interfaces:**
- Produces: `run_tests(code: str, entry_point: str, tests: list[dict], compare: str = "exact", timeout: float = 10.0) -> dict` where each `tests` item is `{"args": [...], "expected": ...}`. Returns `{"results": [{"args", "expected", "got", "passed"}], "passed": int, "total": int, "all_passed": bool, "error": str, "timed_out": bool, "runtime_ms": int}`. On a harness/exec error, `error` is set and `results` is `[]`. `compare="unordered"` compares list outputs order-insensitively.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_executor.py`:
```python
from app.executor import run_tests

TWO_SUM = "def two_sum(nums, target):\n    seen = {}\n    for j, x in enumerate(nums):\n        if target - x in seen:\n            return [seen[target - x], j]\n        seen[x] = j\n    return []\n"
TESTS = [{"args": [[2, 7, 11, 15], 9], "expected": [0, 1]},
         {"args": [[3, 3], 6], "expected": [0, 1]}]


def test_run_tests_all_pass():
    r = run_tests(TWO_SUM, "two_sum", TESTS)
    assert r["all_passed"] is True
    assert r["passed"] == 2 and r["total"] == 2
    assert r["results"][0]["passed"] is True


def test_run_tests_reports_wrong_answer():
    bad = "def two_sum(nums, target):\n    return [9, 9]\n"
    r = run_tests(bad, "two_sum", TESTS)
    assert r["all_passed"] is False
    assert r["passed"] == 0
    assert r["results"][0]["got"] == [9, 9]


def test_run_tests_reports_exec_error():
    r = run_tests("def two_sum(nums, target):\n    return undefined_name\n", "two_sum", TESTS)
    assert r["all_passed"] is False
    assert r["results"][0]["passed"] is False
    assert "NameError" in (r["results"][0]["got"] or r["error"])


def test_run_tests_missing_entry_point():
    r = run_tests("x = 1\n", "two_sum", TESTS)
    assert r["all_passed"] is False
    assert "two_sum" in r["error"]


def test_run_tests_unordered_compare():
    code = "def subsets_count(xs):\n    return [3, 1, 2]\n"
    tests = [{"args": [[1, 2, 3]], "expected": [1, 2, 3]}]
    assert run_tests(code, "subsets_count", tests, compare="exact")["all_passed"] is False
    assert run_tests(code, "subsets_count", tests, compare="unordered")["all_passed"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_executor.py -k run_tests -v`
Expected: FAIL — `ImportError: cannot import name 'run_tests'`

- [ ] **Step 3: Implement run_tests()**

Append to `app/executor.py`:
```python
import json

_HARNESS = r'''
import json, sys, traceback

def _norm(v, mode):
    if mode == "unordered" and isinstance(v, list):
        try:
            return sorted(v, key=lambda z: json.dumps(z, sort_keys=True))
        except TypeError:
            return v
    return v

def _main():
    payload = json.loads(sys.stdin.read())
    ns = {}
    try:
        exec(payload["code"], ns)
    except Exception:
        print(json.dumps({"harness_error": "Error while loading your code:\n" + traceback.format_exc()}))
        return
    fn = ns.get(payload["entry_point"])
    if not callable(fn):
        print(json.dumps({"harness_error": f"No function named {payload['entry_point']!r} was defined."}))
        return
    mode = payload.get("compare", "exact")
    results = []
    for t in payload["tests"]:
        row = {"args": t["args"], "expected": t["expected"]}
        try:
            got = fn(*t["args"])
            row["got"] = got
            row["passed"] = _norm(got, mode) == _norm(t["expected"], mode)
        except Exception:
            row["got"] = traceback.format_exc().strip().splitlines()[-1]
            row["passed"] = False
        results.append(row)
    print(json.dumps({"results": results}))

_main()
'''


def run_tests(code: str, entry_point: str, tests: list[dict],
              compare: str = "exact", timeout: float = 10.0) -> dict:
    payload = json.dumps({"code": code, "entry_point": entry_point,
                          "tests": tests, "compare": compare})
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "harness.py"
        harness.write_text(_HARNESS, encoding="utf-8")
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, str(harness)], input=payload,
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return {"results": [], "passed": 0, "total": len(tests),
                    "all_passed": False, "error": f"Timed out after {timeout:g}s",
                    "timed_out": True,
                    "runtime_ms": int((time.perf_counter() - start) * 1000)}
        runtime_ms = int((time.perf_counter() - start) * 1000)
        try:
            out = json.loads(proc.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            return {"results": [], "passed": 0, "total": len(tests),
                    "all_passed": False,
                    "error": proc.stderr or "No output from test harness.",
                    "timed_out": False, "runtime_ms": runtime_ms}
        if "harness_error" in out:
            return {"results": [], "passed": 0, "total": len(tests),
                    "all_passed": False, "error": out["harness_error"],
                    "timed_out": False, "runtime_ms": runtime_ms}
        results = out["results"]
        passed = sum(1 for r in results if r["passed"])
        return {"results": results, "passed": passed, "total": len(results),
                "all_passed": passed == len(results) and len(results) > 0,
                "error": "", "timed_out": False, "runtime_ms": runtime_ms}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_executor.py -v`
Expected: PASS (8 passed total in the file)

- [ ] **Step 5: Commit**

```bash
git add app/executor.py tests/test_executor.py
git commit -m "feat: add executor.run_tests with ordered/unordered comparison"
```

---

### Task 5: Scheduler — result→quality mapping and SM-2 update

**Files:**
- Create: `app/scheduler.py`, `tests/test_scheduler.py`

**Interfaces:**
- Produces:
  - `quality_from_result(result: str, elapsed_ms: int, target_ms: int) -> int` — `result` in {`"clean"`,`"peeked"`,`"failed"`}. clean & `elapsed_ms <= target_ms` → 5; clean & slower → 4; peeked → 2; failed → 1.
  - `update_sm2(state: dict, quality: int, today: str, intervals: list[int]) -> dict` — `state` has `ease, interval, repetitions, due, last_result`; `today` is ISO date `"YYYY-MM-DD"`. Returns a NEW state dict. Implements SM-2: quality < 3 resets repetitions to 0 and interval to 1 day; otherwise repetitions increments and interval follows `intervals` for the first reps then `round(interval * ease)`; ease updated by the SM-2 formula, floored at 1.3. `due` = today + interval days.
- Consumes: nothing.

- [ ] **Step 1: Write the failing tests**

`tests/test_scheduler.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_scheduler.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.scheduler'`

- [ ] **Step 3: Implement quality + SM-2**

`app/scheduler.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_scheduler.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add app/scheduler.py tests/test_scheduler.py
git commit -m "feat: add SM-2 scheduling and result-to-quality mapping"
```

---

### Task 6: Scheduler — concept mastery and next-problem recommendation

**Files:**
- Modify: `app/scheduler.py`, `tests/test_scheduler.py`

**Interfaces:**
- Produces:
  - `update_concepts(mastery: dict, concepts: list[str], clean: bool) -> dict` — returns NEW mastery mapping `{tag: {"attempts": int, "cleans": int}}` with `concepts` incremented (`cleans` only when `clean`).
  - `concept_rate(mastery: dict, tag: str) -> float` — cleans/attempts, or `0.0` if unseen (unseen counts as weakest).
  - `recommend_next(problems: list[dict], schedule: dict, today: str, config: dict) -> dict` — `problems` are dicts with `slug, difficulty, concepts`; `schedule` is `{"problems": {slug: sm2state}, "concepts": mastery}`. Returns `{"recommended": slug|None, "due": [slug...], "reason": str, "stats": {"total": int, "seen": int, "due_count": int}}`. Logic: (1) if any seen problem has `due <= today`, recommend the most-overdue (smallest `due`); reason `"review"`. (2) else pick an unseen problem; if `config["weak_concept_bias"]`, choose the unseen problem whose weakest concept has the lowest `concept_rate`; reason `"new"`. (3) if nothing left, `recommended=None`, reason `"done"`.
- Consumes: `quality_from_result`, `update_sm2` from Task 5 (unchanged).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_scheduler.py`:
```python
from app.scheduler import update_concepts, concept_rate, recommend_next

CONFIG = {"weak_concept_bias": True, "daily_new": 2}

PROBLEMS = [
    {"slug": "two-sum", "difficulty": "Easy", "concepts": ["hashing"]},
    {"slug": "coin-change", "difficulty": "Medium", "concepts": ["dp"]},
    {"slug": "num-islands", "difficulty": "Medium", "concepts": ["graphs"]},
]


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_scheduler.py -k "concept or recommend" -v`
Expected: FAIL — `ImportError: cannot import name 'update_concepts'`

- [ ] **Step 3: Implement concepts + recommendation**

Append to `app/scheduler.py`:
```python
def update_concepts(mastery: dict, concepts: list[str], clean: bool) -> dict:
    out = {k: dict(v) for k, v in mastery.items()}
    for tag in concepts:
        row = out.setdefault(tag, {"attempts": 0, "cleans": 0})
        row["attempts"] += 1
        if clean:
            row["cleans"] += 1
    return out


def concept_rate(mastery: dict, tag: str) -> float:
    row = mastery.get(tag)
    if not row or row["attempts"] == 0:
        return 0.0
    return row["cleans"] / row["attempts"]


def recommend_next(problems: list[dict], schedule: dict, today: str, config: dict) -> dict:
    sched_problems = schedule.get("problems", {})
    mastery = schedule.get("concepts", {})

    due = sorted(
        (slug for slug, st in sched_problems.items() if st.get("due") and st["due"] <= today),
        key=lambda s: sched_problems[s]["due"],
    )
    stats = {"total": len(problems), "seen": len(sched_problems), "due_count": len(due)}

    if due:
        return {"recommended": due[0], "due": due, "reason": "review", "stats": stats}

    unseen = [p for p in problems if p["slug"] not in sched_problems]
    if not unseen:
        return {"recommended": None, "due": [], "reason": "done", "stats": stats}

    if config.get("weak_concept_bias", True):
        def weakness(p):
            return min((concept_rate(mastery, c) for c in p["concepts"]), default=0.0)
        unseen.sort(key=weakness)

    return {"recommended": unseen[0]["slug"], "due": [], "reason": "new", "stats": stats}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_scheduler.py -v`
Expected: PASS (14 passed total in the file)

- [ ] **Step 5: Commit**

```bash
git add app/scheduler.py tests/test_scheduler.py
git commit -m "feat: add concept mastery and next-problem recommendation"
```

---

### Task 7: Storage — schedule and session persistence

**Files:**
- Create: `app/storage.py`, `tests/test_storage.py`

**Interfaces:**
- Produces:
  - `load_problems(problems_dir: Path) -> dict[str, Problem]` — slug → Problem for every `*.json`.
  - `load_schedule(path: Path) -> dict` — returns `{"problems": {}, "concepts": {}}` if missing OR corrupt (never raises).
  - `save_schedule(path: Path, schedule: dict) -> None` — atomic write (temp + replace), creates parent dir.
  - `load_config(path: Path, defaults: dict) -> dict` — defaults if missing; merges missing keys.
  - `append_session(sessions_dir: Path, session: dict) -> Path` — writes `<sessions_dir>/<timestamp-slug>.json`; caller supplies a `timestamp` key (ISO string) and `slug`; returns the path.
  - `record_attempt(schedule, slug, problem, result, elapsed_ms, today, config) -> dict` — pure: computes quality, updates that problem's SM-2 state and concept mastery, returns a NEW schedule dict (does not write).
- Consumes: `Problem.from_file` (Task 2); `quality_from_result`, `update_sm2`, `update_concepts` (Tasks 5-6).

- [ ] **Step 1: Write the failing tests**

`tests/test_storage.py`:
```python
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


def test_record_attempt_updates_schedule_and_concepts():
    problems = storage.load_problems(config.PROBLEMS_DIR)
    p = problems["two-sum"]
    schedule = {"problems": {}, "concepts": {}}
    out = storage.record_attempt(schedule, "two-sum", p, "clean", 5 * 60_000,
                                 "2026-07-01", config.DEFAULT_CONFIG)
    assert out["problems"]["two-sum"]["repetitions"] == 1
    assert out["concepts"]["hashing"] == {"attempts": 1, "cleans": 1}
    # original not mutated
    assert schedule["problems"] == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_storage.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.storage'`

- [ ] **Step 3: Implement storage**

`app/storage.py`:
```python
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
from app.models import Problem
from app.scheduler import quality_from_result, update_sm2, update_concepts

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
    name = f"{session['timestamp']}-{session['slug']}.json"
    path = sessions_dir / name
    path.write_text(json.dumps(session, indent=2), encoding="utf-8")
    return path


def record_attempt(schedule: dict, slug: str, problem: Problem, result: str,
                   elapsed_ms: int, today: str, config: dict) -> dict:
    problems = {k: dict(v) for k, v in schedule.get("problems", {}).items()}
    target_min = config["target_minutes"].get(problem.difficulty, 20)
    quality = quality_from_result(result, elapsed_ms, target_min * 60_000)
    state = problems.get(slug, {"ease": config["starting_ease"], "interval": 0,
                                "repetitions": 0, "due": None, "last_result": None})
    new_state = update_sm2(state, quality, today, config["initial_intervals"])
    new_state["last_result"] = result
    problems[slug] = new_state
    concepts = update_concepts(schedule.get("concepts", {}), problem.concepts,
                               clean=(result == "clean"))
    return {"problems": problems, "concepts": concepts}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_storage.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add app/storage.py tests/test_storage.py
git commit -m "feat: add storage for problems, schedule, sessions, attempts"
```

---

### Task 8: FastAPI routes

**Files:**
- Create: `app/main.py`, `tests/test_api.py`

**Interfaces:**
- Produces a FastAPI `app` with JSON routes under `/api`:
  - `GET /api/problems` → `[{slug, title, difficulty, concepts, seen: bool, due: str|None}]`.
  - `GET /api/problem/{slug}` → full problem dict (includes solutions; the frontend hides them).
  - `POST /api/run` body `{code}` → `executor.run` result.
  - `POST /api/submit` body `{slug, code}` → `executor.run_tests` result.
  - `POST /api/attempt` body `{slug, code, elapsed_ms, result, notes}` → `{schedule_state, next}`; writes schedule + appends a session.
  - `GET /api/next` → `scheduler.recommend_next` output.
  - `GET /api/config` / `POST /api/config` → read/update config.
  - Static frontend mounted at `/` from `config.FRONTEND_DIR`.
- Consumes: everything from Tasks 2-7.
- Note: `_now_iso()` and `_today()` are module-level helpers so tests can monkeypatch them for determinism.

- [ ] **Step 1: Write the failing tests**

`tests/test_api.py`:
```python
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
    slugs = [p["slug"] for p in r.json()]
    assert "two-sum" in slugs


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
        "result": "clean", "notes": {"restate": "find two indices"},
    })
    body = r.json()
    assert body["schedule_state"]["repetitions"] == 1
    assert "next" in body
    # persisted: listing now shows two-sum as seen
    r2 = client.get("/api/problems")
    two = next(p for p in r2.json() if p["slug"] == "two-sum")
    assert two["seen"] is True


def test_next_endpoint(client):
    assert client.get("/api/next").json()["reason"] in {"review", "new", "done"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 3: Implement the API**

`app/main.py`:
```python
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app import config, storage, executor, scheduler

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
    result: str
    notes: dict = {}


@app.get("/api/problems")
def list_problems():
    schedule = storage.load_schedule(config.SCHEDULE_PATH)
    seen = schedule["problems"]
    out = []
    for slug, p in _problems().items():
        st = seen.get(slug)
        out.append({"slug": slug, "title": p.title, "difficulty": p.difficulty,
                    "concepts": p.concepts, "seen": st is not None,
                    "due": st.get("due") if st else None})
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
    return executor.run_tests(body.code, p.entry_point,
                              [t.model_dump() for t in p.tests], p.compare)


@app.post("/api/attempt")
def attempt(body: AttemptBody):
    problems = _problems()
    p = problems.get(body.slug)
    if not p:
        raise HTTPException(404, f"No problem {body.slug!r}")
    cfg = _config()
    today = _today()
    schedule = storage.load_schedule(config.SCHEDULE_PATH)
    schedule = storage.record_attempt(schedule, body.slug, p, body.result,
                                      body.elapsed_ms, today, cfg)
    storage.save_schedule(config.SCHEDULE_PATH, schedule)
    storage.append_session(config.SESSIONS_DIR, {
        "timestamp": _now_iso(), "slug": body.slug, "result": body.result,
        "elapsed_ms": body.elapsed_ms, "code": body.code, "notes": body.notes,
    })
    prob_dicts = [{"slug": s, "difficulty": pr.difficulty, "concepts": pr.concepts}
                  for s, pr in problems.items()]
    nxt = scheduler.recommend_next(prob_dicts, schedule, today, cfg)
    return {"schedule_state": schedule["problems"][body.slug], "next": nxt}


@app.get("/api/next")
def next_problem():
    problems = _problems()
    schedule = storage.load_schedule(config.SCHEDULE_PATH)
    prob_dicts = [{"slug": s, "difficulty": p.difficulty, "concepts": p.concepts}
                  for s, p in problems.items()]
    return scheduler.recommend_next(prob_dicts, schedule, _today(), _config())


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
```

Note: `set_config` reuses `storage.save_schedule` purely as a generic atomic JSON writer — acceptable since both are plain-dict JSON. If a reviewer objects, add a `save_json` alias; functionally identical.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_api.py -v`
Expected: PASS (6 passed). The `/` static mount is skipped in tests until the frontend exists — that's fine; `test_*` only hit `/api/*`.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -v`
Expected: PASS (all tests from Tasks 1-8)

- [ ] **Step 6: Commit**

```bash
git add app/main.py tests/test_api.py
git commit -m "feat: add FastAPI routes for problems, run, submit, attempt, next"
```

---

### Task 9: Frontend — three-column layout, editor, run/submit

**Files:**
- Create: `app/frontend/index.html`, `app/frontend/style.css`, `app/frontend/app.js`

**Interfaces:**
- Consumes the `/api/*` routes from Task 8.
- Produces the static SPA. CodeMirror 5 is loaded from CDN (Python mode + a dark theme) — chosen for zero build step and a single `<script>` include.

- [ ] **Step 1: Create index.html**

`app/frontend/index.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>reps — coding gym</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.css" />
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/theme/material-darker.min.css" />
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <header id="topbar">
    <span id="brand">reps</span>
    <span id="problem-title">—</span>
    <span id="timer-wrap">
      <input id="timer-minutes" type="number" min="1" max="120" value="20" />
      <button id="timer-start">Start</button>
      <button id="timer-pause">Pause</button>
      <button id="timer-reset">Reset</button>
      <span id="timer-display">20:00</span>
    </span>
    <button id="next-btn">What's next?</button>
  </header>

  <main id="columns">
    <section id="col-problem">
      <div id="problem-desc"></div>
      <div id="hints"></div>
      <details id="solution-block"><summary>Show solution (marks as peeked)</summary>
        <div id="solutions"></div>
      </details>
    </section>

    <section id="col-editor">
      <textarea id="code"></textarea>
      <div id="editor-actions">
        <button id="run-btn">Run</button>
        <button id="submit-btn">Submit</button>
        <button id="mark-clean" title="Log this as solved unaided">I solved it (clean)</button>
      </div>
    </section>

    <section id="col-results">
      <div id="results"></div>
      <div id="notes">
        <h3>R.E.P.S. notes</h3>
        <label>Restate<textarea data-note="restate"></textarea></label>
        <label>Examples<textarea data-note="examples"></textarea></label>
        <label>Plan<textarea data-note="plan"></textarea></label>
        <label>Step &amp; speak<textarea data-note="step"></textarea></label>
      </div>
    </section>
  </main>

  <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/python/python.min.js"></script>
  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create style.css**

`app/frontend/style.css`:
```css
* { box-sizing: border-box; }
body { margin: 0; font-family: system-ui, sans-serif; background:#1e1e1e; color:#ddd; height:100vh; display:flex; flex-direction:column; }
#topbar { display:flex; align-items:center; gap:12px; padding:8px 14px; background:#252526; border-bottom:1px solid #333; }
#brand { font-weight:700; color:#4ec9b0; letter-spacing:1px; }
#problem-title { font-weight:600; }
#timer-wrap { margin-left:auto; display:flex; align-items:center; gap:6px; }
#timer-display { font-variant-numeric:tabular-nums; font-size:20px; min-width:70px; text-align:center; }
#timer-display.overtime { color:#f48771; }
#timer-minutes { width:56px; }
button { background:#0e639c; color:#fff; border:0; padding:6px 12px; border-radius:4px; cursor:pointer; }
button:hover { background:#1177bb; }
#columns { flex:1; display:grid; grid-template-columns: 1fr 1fr 1fr; gap:1px; background:#333; overflow:hidden; }
#columns > section { background:#1e1e1e; overflow:auto; padding:12px; display:flex; flex-direction:column; }
#problem-desc { line-height:1.5; }
#problem-desc pre, #solutions pre { background:#111; padding:8px; border-radius:4px; overflow:auto; }
.CodeMirror { height:auto; flex:1; min-height:300px; border:1px solid #333; font-size:14px; }
#editor-actions { margin-top:8px; display:flex; gap:8px; }
#results { white-space:pre-wrap; font-family:ui-monospace, monospace; min-height:120px; }
.case { padding:6px; border-radius:4px; margin:4px 0; }
.case.pass { background:#122d12; } .case.fail { background:#3a1414; }
#notes { margin-top:14px; } #notes label { display:block; font-size:12px; color:#9cdcfe; margin-top:6px; }
#notes textarea, #code { width:100%; }
#notes textarea { height:44px; background:#252526; color:#ddd; border:1px solid #333; border-radius:4px; }
#hints button { background:#5a4a00; margin:6px 0; } .hint { background:#2a2a1a; padding:6px; border-radius:4px; margin:4px 0; }
```

- [ ] **Step 3: Create app.js (editor + run/submit; timer/notes/next in later tasks stubbed)**

`app/frontend/app.js`:
```javascript
const $ = (sel) => document.querySelector(sel);
let editor, currentProblem = null, aided = false;

async function api(path, opts) {
  const r = await fetch("/api" + path, opts);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
function post(path, body) {
  return api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

function initEditor() {
  editor = CodeMirror.fromTextArea($("#code"), {
    mode: "python", theme: "material-darker", lineNumbers: true,
    indentUnit: 4, matchBrackets: true,
  });
}

async function loadProblem(slug) {
  const p = await api("/problem/" + slug);
  currentProblem = p; aided = false;
  $("#problem-title").textContent = p.title + "  ·  " + p.difficulty;
  $("#problem-desc").innerHTML = renderMarkdown(p.description);
  renderHints(p.hints);
  renderSolutions(p.solutions);
  editor.setValue(p.starter_code || "");
  $("#results").textContent = "";
}

function renderMarkdown(md) {
  // Minimal: fence code blocks and preserve line breaks. Good enough for problem text.
  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return esc(md)
    .replace(/```([\s\S]*?)```/g, (_, c) => "<pre>" + c.trim() + "</pre>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br/>");
}

function renderHints(hints) {
  const box = $("#hints"); box.innerHTML = "";
  (hints || []).forEach((h, i) => {
    const btn = document.createElement("button");
    btn.textContent = "Hint " + (i + 1);
    btn.onclick = () => {
      const d = document.createElement("div"); d.className = "hint"; d.textContent = h;
      box.replaceChild(d, btn);
    };
    box.appendChild(btn);
  });
}

function renderSolutions(sols) {
  const box = $("#solutions"); box.innerHTML = "";
  (sols || []).forEach((s) => {
    const el = document.createElement("div");
    el.innerHTML = "<h4>" + s.name + "</h4><p>" + s.explanation + "</p><pre>" +
      s.code.replace(/</g, "&lt;") + "</pre><em>" + s.complexity + "</em>";
    box.appendChild(el);
  });
}

async function runCode() {
  $("#results").textContent = "Running…";
  const r = await post("/run", { code: editor.getValue() });
  $("#results").textContent = (r.stdout || "") + (r.error ? "\n" + r.error : "");
}

async function submitCode() {
  $("#results").innerHTML = "Running tests…";
  const r = await post("/submit", { slug: currentProblem.slug, code: editor.getValue() });
  const box = $("#results"); box.innerHTML = "";
  if (r.error) { box.textContent = r.error; return; }
  const head = document.createElement("div");
  head.textContent = `${r.passed}/${r.total} passed · ${r.runtime_ms}ms`;
  box.appendChild(head);
  r.results.forEach((c) => {
    const d = document.createElement("div");
    d.className = "case " + (c.passed ? "pass" : "fail");
    d.textContent = `${c.passed ? "✓" : "✗"} args=${JSON.stringify(c.args)} → got ${JSON.stringify(c.got)} · want ${JSON.stringify(c.expected)}`;
    box.appendChild(d);
  });
  window._lastAllPassed = r.all_passed;
}

function wire() {
  $("#run-btn").onclick = runCode;
  $("#submit-btn").onclick = submitCode;
}

window.addEventListener("DOMContentLoaded", async () => {
  initEditor();
  wire();
  // Load the recommended next problem on open (falls back to first problem).
  const nxt = await api("/next");
  const slug = nxt.recommended || (await api("/problems"))[0]?.slug;
  if (slug) loadProblem(slug);
});
```

- [ ] **Step 4: Manual verification**

Run: `uv run uvicorn app.main:app --port 8000` then open `http://127.0.0.1:8000`.
Expected: three columns render; Two Sum loads with syntax-highlighted starter code; `Run` prints output; `Submit` shows per-case pass/fail. Stop the server (Ctrl-C) when done.

- [ ] **Step 5: Commit**

```bash
git add app/frontend
git commit -m "feat: add three-column frontend with editor, run, and submit"
```

---

### Task 10: Frontend — timer and R.E.P.S. notes wiring

**Files:**
- Modify: `app/frontend/app.js`

**Interfaces:**
- Consumes: existing DOM ids from Task 9 (`#timer-*`, `#notes textarea[data-note]`).
- Produces: `getElapsedMs()` and `getNotes()` helpers used by Task 11's attempt submission; a running countdown that turns red past zero.

- [ ] **Step 1: Add timer + notes logic**

Append to `app/frontend/app.js` (before the `DOMContentLoaded` handler):
```javascript
let timer = { total: 20 * 60, remaining: 20 * 60, id: null, startedAt: null, elapsedMs: 0 };

function fmt(sec) {
  const s = Math.max(0, Math.abs(sec));
  const m = Math.floor(s / 60), r = s % 60;
  return (sec < 0 ? "-" : "") + String(m).padStart(2, "0") + ":" + String(r).padStart(2, "0");
}
function paintTimer() {
  const d = $("#timer-display");
  d.textContent = fmt(timer.remaining);
  d.classList.toggle("overtime", timer.remaining < 0);
}
function tickTimer() {
  timer.remaining -= 1;
  timer.elapsedMs += 1000;
  paintTimer();
}
function startTimer() {
  if (timer.id) return;
  timer.startedAt = Date.now();
  timer.id = setInterval(tickTimer, 1000);
}
function pauseTimer() { clearInterval(timer.id); timer.id = null; }
function resetTimer() {
  pauseTimer();
  timer.total = (parseInt($("#timer-minutes").value, 10) || 20) * 60;
  timer.remaining = timer.total; timer.elapsedMs = 0;
  paintTimer();
}
function getElapsedMs() { return timer.elapsedMs; }
function getNotes() {
  const notes = {};
  document.querySelectorAll("#notes textarea[data-note]").forEach((t) => notes[t.dataset.note] = t.value);
  return notes;
}
function clearNotes() { document.querySelectorAll("#notes textarea[data-note]").forEach((t) => t.value = ""); }

function wireTimer() {
  $("#timer-start").onclick = startTimer;
  $("#timer-pause").onclick = pauseTimer;
  $("#timer-reset").onclick = resetTimer;
  $("#timer-minutes").onchange = resetTimer;
}
```

- [ ] **Step 2: Call wireTimer() on load**

In `app.js`, inside the `wire()` function add:
```javascript
  wireTimer();
```

- [ ] **Step 3: Manual verification**

Run the server; set minutes to 1, Start — display counts down, passes 00:00 into negative red time; Pause/Reset behave. Notes textareas accept text.

- [ ] **Step 4: Commit**

```bash
git add app/frontend/app.js
git commit -m "feat: wire countdown timer and R.E.P.S. notes capture"
```

---

### Task 11: Frontend — attempt submission, solution auto-peek, next-problem flow

**Files:**
- Modify: `app/frontend/app.js`

**Interfaces:**
- Consumes: `/api/attempt`, `/api/next`, `getElapsedMs()`, `getNotes()`, `window._lastAllPassed`.
- Produces the completion loop: logging clean/failed, auto-`peeked` on solution reveal, and loading the recommended next problem.

- [ ] **Step 1: Add attempt + next logic**

Append to `app/frontend/app.js` (before `DOMContentLoaded`):
```javascript
async function finishAttempt(result) {
  if (!currentProblem) return;
  pauseTimer();
  const body = {
    slug: currentProblem.slug, code: editor.getValue(),
    elapsed_ms: getElapsedMs(), result, notes: getNotes(),
  };
  const res = await post("/attempt", body);
  const n = res.next;
  const msg = n.recommended
    ? `Logged "${result}". Next up: ${n.recommended} (${n.reason}).`
    : `Logged "${result}". Nothing due — you're clear.`;
  if (confirm(msg + "\n\nLoad next problem now?") && n.recommended) {
    clearNotes(); resetTimer(); loadProblem(n.recommended);
  }
}

async function goNext() {
  const n = await api("/next");
  if (!n.recommended) { alert("Nothing due right now. Add problems or come back later."); return; }
  clearNotes(); resetTimer(); loadProblem(n.recommended);
}

function markCleanIfSolved() {
  if (window._lastAllPassed && !aided) finishAttempt("clean");
  else if (aided) finishAttempt("peeked");
  else alert("Submit first and pass all tests before logging a clean solve.");
}
```

- [ ] **Step 2: Wire the completion buttons and auto-peek**

In `app.js` `wire()`, add:
```javascript
  $("#mark-clean").onclick = markCleanIfSolved;
  $("#next-btn").onclick = goNext;
  $("#solution-block").addEventListener("toggle", (e) => {
    if (e.target.open && currentProblem) { aided = true; finishAttempt("peeked"); }
  });
```

- [ ] **Step 3: Manual verification**

Run the server. Solve Two Sum, Submit (all pass), click "I solved it (clean)" → confirm dialog offers the next problem; reload shows Two Sum as seen. On a fresh problem, expand "Show solution" → it auto-logs `peeked` and offers next.

- [ ] **Step 4: Commit**

```bash
git add app/frontend/app.js
git commit -m "feat: add attempt logging, solution auto-peek, and next-problem flow"
```

---

### Task 12: Launcher + full-app smoke test

**Files:**
- Create: `reps.py`, `tests/test_smoke.py`

**Interfaces:**
- Produces: `reps.py` runnable via `uv run python reps.py` — ensures data dirs, opens the browser, starts uvicorn on `127.0.0.1:8000`.

- [ ] **Step 1: Write the launcher**

`reps.py`:
```python
"""Launch the reps coding gym: start the server and open the browser."""
import threading
import webbrowser
import uvicorn
from app import config

HOST, PORT = "127.0.0.1", 8000


def _open_browser():
    webbrowser.open(f"http://{HOST}:{PORT}")


if __name__ == "__main__":
    config.ensure_dirs()
    threading.Timer(1.0, _open_browser).start()
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="info")
```

- [ ] **Step 2: Write a smoke test that the app boots and serves the page**

`tests/test_smoke.py`:
```python
from fastapi.testclient import TestClient
import app.main as main


def test_index_served():
    client = TestClient(main.app)
    r = client.get("/")
    assert r.status_code == 200
    assert "reps" in r.text.lower()
```

- [ ] **Step 3: Run the smoke test**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: PASS (serves `index.html` from the static mount)

- [ ] **Step 4: Manual end-to-end**

Run: `uv run python reps.py`
Expected: browser opens to the gym; full loop works (load → code → run → submit → log → next).

- [ ] **Step 5: Commit**

```bash
git add reps.py tests/test_smoke.py
git commit -m "feat: add launcher and full-app smoke test"
```

---

### Task 13: Seed the Blind 75 starter set (~15–20 problems)

**Files:**
- Create: `problems/*.json` (14–19 more, covering the pattern sequence)
- Create: `tests/test_problems_valid.py`

**Interfaces:**
- Each new problem follows the Task 2 schema exactly. Pattern coverage (each has original description + tests + ≥1 solution): hashing/arrays (two-sum ✓, contains-duplicate, valid-anagram), two-pointer (valid-palindrome, 3sum), sliding-window (best-time-buy-sell-stock, longest-substring-without-repeating), binary-search (search-rotated-sorted-array), trees (invert-binary-tree, max-depth-binary-tree, same-tree — use list-serialized trees or plain recursion helpers embedded in starter code), graphs (number-of-islands), backtracking (subsets), dp (climbing-stairs, coin-change, house-robber), heaps/intervals (merge-intervals), linked-list (reverse-linked-list — represent lists as Python lists in/out to keep `entry_point` simple).
- Note: to keep every problem executable through the simple `entry_point(*args)` harness, design signatures around plain built-in types (lists, ints, strings). For tree/linked-list problems, either (a) accept level-order lists and build the structure inside the reference solution, or (b) phrase the problem around list I/O. Document the chosen convention in each problem's description.

- [ ] **Step 1: Write the validation test FIRST**

`tests/test_problems_valid.py`:
```python
import pytest
from app import config, storage
from app.executor import run_tests

PROBLEMS = storage.load_problems(config.PROBLEMS_DIR)


@pytest.mark.parametrize("slug", list(PROBLEMS.keys()))
def test_reference_solution_passes_its_own_tests(slug):
    p = PROBLEMS[slug]
    assert p.solutions, f"{slug} has no reference solution"
    ref = p.solutions[-1].code  # last = optimal
    r = run_tests(ref, p.entry_point, [t.model_dump() for t in p.tests], p.compare)
    assert r["all_passed"], f"{slug} reference solution failed: {r}"


@pytest.mark.parametrize("slug", list(PROBLEMS.keys()))
def test_problem_has_required_fields(slug):
    p = PROBLEMS[slug]
    assert p.source == "Blind75"
    assert p.concepts and p.tests and p.hints
    assert p.entry_point in p.starter_code
```

- [ ] **Step 2: Run it (only two-sum exists) to confirm the harness works**

Run: `uv run pytest tests/test_problems_valid.py -v`
Expected: PASS for `two-sum` (both params).

- [ ] **Step 3: Author each problem file**

For each problem listed above, create `problems/<slug>.json` with original wording. Work in small batches (3–4 files), running Step 4 after each batch. Example second problem — `problems/contains-duplicate.json`:
```json
{
  "slug": "contains-duplicate",
  "title": "Contains Duplicate",
  "difficulty": "Easy",
  "concepts": ["hashing", "arrays"],
  "source": "Blind75",
  "description": "Given a list of integers `nums`, return `true` if any value appears at least twice, and `false` if every element is distinct.\n\n**Example**\n\n```\nnums = [1, 2, 3, 1]  ->  true\nnums = [1, 2, 3, 4]  ->  false\n```",
  "entry_point": "contains_duplicate",
  "starter_code": "def contains_duplicate(nums):\n    # Return True if any value repeats.\n    pass\n",
  "compare": "exact",
  "tests": [
    {"args": [[1, 2, 3, 1]], "expected": true},
    {"args": [[1, 2, 3, 4]], "expected": false},
    {"args": [[]], "expected": false}
  ],
  "hints": ["A set remembers what you've already seen.", "If len(set(nums)) < len(nums), there was a duplicate."],
  "solutions": [
    {"name": "Set", "explanation": "Add elements to a set as you scan; if you ever see one already present, you found a duplicate. Equivalently, compare the size of the set to the list length.", "code": "def contains_duplicate(nums):\n    seen = set()\n    for x in nums:\n        if x in seen:\n            return True\n        seen.add(x)\n    return False\n", "complexity": "Time O(n), Space O(n)"}
  ]
}
```
Author the remaining problems following this exact shape. For DP/graph/tree problems, keep signatures on plain types (e.g. `climbing_stairs(n) -> int`, `number_of_islands(grid) -> int` with `grid` a list of list of "1"/"0" strings, `coin_change(coins, amount) -> int`, `reverse_linked_list(values) -> list`).

- [ ] **Step 4: Validate the whole library after each batch**

Run: `uv run pytest tests/test_problems_valid.py -v`
Expected: PASS for every problem (reference solution passes its own tests; required fields present). Fix any failing problem before continuing.

- [ ] **Step 5: Commit (per batch is fine)**

```bash
git add problems tests/test_problems_valid.py
git commit -m "feat: seed Blind 75 starter problems across core patterns"
```

---

### Task 14: README and final verification

**Files:**
- Modify: `README.md`

**Interfaces:** none (docs + verification).

- [ ] **Step 1: Write the README**

`README.md`:
```markdown
# reps — coding interview gym

A local three-column coding-interview gym for **Blind 75** practice: live Python
execution, syntax highlighting, an adjustable countdown timer, R.E.P.S.-structured
notes, and SM-2 + concept-tag spaced repetition that tells you your next problem.

## Run

```bash
uv run python reps.py
```

Opens http://127.0.0.1:8000. The gym loads your recommended next problem on start.

## Daily loop

1. Open the app — it picks your next problem (a due review, else a new one from
   your weakest concept).
2. Start the timer (default 20 min). Work the R.E.P.S. protocol in the notes pane.
3. `Run` to scratch-test, `Submit` to check against hidden tests.
4. Log the result: **I solved it (clean)** after passing, or expand **Show
   solution** (auto-logs *peeked* and schedules a redo).

## Add a problem

Drop a JSON file in `problems/` (see any existing file for the schema). Validate:

```bash
uv run pytest tests/test_problems_valid.py
```

## Data

Your progress lives in `data/` (gitignored): `schedule.json` (SM-2 + concept
mastery), `sessions/` (one file per attempt — code, timing, notes). This is the
corpus a future AI coach (Phase 2) will analyze.

## Tests

```bash
uv run pytest
```
```

- [ ] **Step 2: Run the full suite**

Run: `uv run pytest -v`
Expected: PASS (all tests, all seeded problems valid).

- [ ] **Step 3: Final manual end-to-end**

Run `uv run python reps.py`; complete one full problem loop and confirm `data/schedule.json` and a `data/sessions/*.json` file were written.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add README with run instructions and daily loop"
```

---

## Self-Review

**Spec coverage:**
- Three-column layout → Task 9. Live Python execution → Tasks 3-4, 8. Syntax highlighting → Task 9 (CodeMirror). Adjustable timer → Task 10. R.E.P.S. notes capture → Tasks 9-10. Blind 75 library + starter set → Tasks 2, 13. Solutions + explanations + auto-peek → Tasks 2, 9, 11. SM-2 + concept scheduling → Tasks 5-6. Session-start "what's next" → Tasks 6, 8, 9, 11. File persistence in `reps/` → Tasks 1, 7. Configurable scheduler → Tasks 1, 7, 8. Error handling (timeout, tracebacks, corrupt state) → Tasks 3-4, 7. Testing (pytest TDD) → every backend task; problem-validity guard → Task 13. Launcher → Task 12. AI deferred but data captured → notes/sessions written in Tasks 8, 10, 11. All spec sections map to tasks.
- **Deferred correctly:** AI interviewer/analysis (Phase 2) — not in any task, matching the spec.

**Placeholder scan:** No "TBD"/"handle edge cases"/"similar to Task N". Task 13 intentionally lists problems to author with a worked example and an exact schema + a validating test rather than 19 full JSON blobs — each file is mechanical given the schema and is guarded by `test_problems_valid.py`, so this is complete, not a placeholder.

**Type consistency:** `run`/`run_tests` shapes match between executor (Tasks 3-4), API (Task 8), and frontend (Task 9). `update_sm2(state, quality, today, intervals)`, `update_concepts(mastery, concepts, clean)`, `recommend_next(problems, schedule, today, config)` signatures are identical across Tasks 5-8. Schedule shape `{"problems": {...}, "concepts": {...}}` is consistent across storage, scheduler, and API. `record_attempt` returns a schedule dict used directly by `save_schedule`. Frontend helpers `getElapsedMs`/`getNotes` (Task 10) are consumed in Task 11.
