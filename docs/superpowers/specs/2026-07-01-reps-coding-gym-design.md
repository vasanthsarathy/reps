# reps — Coding Interview Gym (Design)

**Date:** 2026-07-01
**Status:** Approved design, Phase 1
**Location:** `2_Areas/Career/Tech_Interview_Prep/reps/`

## Goal

A local, single-user web app that recreates the HackerRank/CoderPad three-column
coding-interview experience for **Blind 75** practice, with **live Python
execution**, **syntax highlighting**, an **adjustable countdown timer**, and a
**spaced-repetition engine** that tells the user which problem to do next. It
exists to serve the user's daily loop (see `../../00_START_HERE.md`) and to drill
the **R.E.P.S. freeze protocol** under time pressure.

The app is named `reps` and deliberately mirrors the user's R.E.P.S. protocol
(Restate / Examples / Plan / Step & speak).

## Scope

**Phase 1 (this spec):** the core coding gym — no AI.
- Three-column layout: problem / editor / results.
- Live Python execution (Run scratchpad + Submit against tests).
- Syntax highlighting + line numbers.
- Adjustable, always-visible countdown timer.
- Blind 75 problem library (seed ~15–20, grow to 75).
- Per-problem solutions + explanations, revealable on demand.
- SM-2 + concept-tag spaced repetition and a "what's next" session-start screen.
- R.E.P.S.-structured notes captured with every attempt.

**Explicitly deferred (Phase 2, not built now):** AI interviewer chat and the
"analyze my thought process" pass. Phase 1 **collects** the raw material (notes,
timings, questions, results) so Phase 2 is purely additive — new backend
endpoints plus a Claude API key in a server-side `.env`. No Phase-1 structure is
reworked to add it.

**Out of scope:** NeetCode 150 (Blind 75 only; more problems are just more JSON,
no code change), languages other than Python, multi-user/accounts, cloud
hosting, authentication.

## Non-goals / YAGNI

- No sandbox/jailing of executed code beyond a subprocess + timeout. It is the
  user's own code on the user's own machine.
- No build toolchain (bundler/transpiler) on the frontend. Libraries load via CDN.
- No database server. State is plain files.

## Architecture

**Thin local Python (FastAPI) backend + static browser frontend.** One command
starts the server and opens the browser.

```
reps/
├── reps.py                 # launcher: starts uvicorn, opens browser
├── requirements.txt        # fastapi, uvicorn
├── app/
│   ├── backend/
│   │   ├── main.py         # FastAPI app + routes
│   │   ├── executor.py     # run user code in subprocess w/ timeout, run tests
│   │   ├── storage.py      # load problems, read/write attempt logs + schedule
│   │   ├── scheduler.py    # SM-2 + concept-mastery logic (pure functions)
│   │   └── models.py       # dataclasses / pydantic schemas
│   └── frontend/
│       ├── index.html
│       ├── style.css
│       └── app.js          # UI, editor (CodeMirror via CDN), timer, fetch calls
├── problems/               # one JSON per problem — the library (version-controlled)
│   ├── two-sum.json
│   └── ...
├── data/                   # personal state (can be gitignored)
│   ├── schedule.json       # per-problem SM-2 state + concept mastery
│   └── sessions/           # one file per attempt (append-only log)
│       └── 2026-07-01T....json
└── docs/superpowers/specs/ # this design + the implementation plan
```

**Why a backend rather than pure in-browser (Pyodide):**
1. Real CPython behavior — real tracebacks, real timing, real `import` if ever wanted.
2. File-based persistence fits the user's workspace philosophy (greppable, owned).
3. Phase 2 AI is additive: endpoints + server-side key, never exposed to the browser.

### Request flow

- Browser is a static SPA served by FastAPI (or opened directly; API calls go to
  `http://127.0.0.1:<port>`).
- `Run` / `Submit` POST the code to the backend; the backend executes it in a
  fresh subprocess and returns structured results.
- Attempt results and notes POST to the backend, which updates `schedule.json`
  and appends a session log.
- The session-start screen GETs the recommended next problem + due list.

## Components

### 1. Editor (frontend)
CodeMirror loaded via CDN — Python mode, syntax highlighting, line numbers,
sensible indentation. Seeded with the problem's `starter_code`. No build step.
(Implementation may use CodeMirror 6 via a prebuilt CDN bundle; fall back to
CodeMirror 5 if CDN/ESM friction arises. Either satisfies the requirement:
Python syntax highlighting + line numbers, no local toolchain.)

### 2. Executor (backend)
- `run(code) -> {stdout, stderr, error, runtime_ms}`: writes code to a temp file,
  runs `python` in a subprocess with a timeout (~10s), captures stdout/stderr,
  returns a clean traceback string on error.
- `run_tests(code, entry_point, tests) -> {results:[{args, expected, got, passed}],
  passed_count, total, runtime_ms, error}`: builds a harness that imports/execs the
  user code, calls `entry_point` on each test's args, compares to `expected`
  (order-insensitive where a problem declares it), captures per-case outcome and
  any traceback. A timeout marks the run as failed, not a crash.
- The subprocess is the isolation boundary; a runaway loop is killed by the timeout.

### 3. Problem library (files)
One JSON per problem:
```json
{
  "slug": "two-sum",
  "title": "Two Sum",
  "difficulty": "Easy",
  "concepts": ["hashing", "arrays"],
  "source": "Blind75",
  "description": "<original markdown; not copied from LeetCode>",
  "entry_point": "two_sum",
  "starter_code": "def two_sum(nums, target):\n    # your code\n    pass\n",
  "tests": [
    {"args": [[2,7,11,15], 9], "expected": [0,1]}
  ],
  "hints": ["What have you already seen as you scan left to right?"],
  "solutions": [
    {
      "name": "Hash map (O(n))",
      "explanation": "<why it works, in prose>",
      "code": "def two_sum(nums, target): ...",
      "complexity": "Time O(n), Space O(n)"
    }
  ]
}
```
Descriptions and solution prose are **original** (LeetCode's wording is theirs).
Adding a problem = dropping in one JSON file; no code change.

### 4. Solutions + explanations (UI)
Collapsed **"Show solution"** reveal in the problem column, plus progressive
**hints** as a lighter step. Revealing the full solution **auto-logs the attempt
as `peeked`**, which demotes the problem in the scheduler and queues a redo —
automating the user's existing "stuck 15 min → read solution → redo in 3 days"
rule. Multiple `solutions` render in order (e.g. brute force → optimal).

### 5. Timer (frontend)
Adjustable countdown, default 20 min (the user's medium target), always visible,
start / pause / reset, quick presets. At zero: a non-blocking visual cue (no
modal, no forced stop). Elapsed time is captured and sent with each attempt.

### 6. Notes pane (frontend) — R.E.P.S. capture
Structured text areas prompting **Restate / Examples / Plan / Step & speak**.
Serves two purposes: drilling the freeze protocol now, and capturing the
thought-process corpus that Phase 2's AI will analyze. Saved with each attempt.

### 7. Scheduler (backend, pure logic — the testable core)
- **Per-problem SM-2 state:** `ease`, `interval` (days), `repetitions`, `due` date,
  `last_result`. Result → quality mapping:
  - `clean` and fast (≤ target time) → quality 5
  - `clean` but slow → quality 4
  - `peeked` → quality 2 (interval reset toward short)
  - `failed` (submitted, tests failing, gave up / timer) → quality 1 (reset)
  Standard SM-2 update of ease/interval/due from quality.
- **Per-concept mastery:** rolling clean-rate per tag (hashing, sliding-window,
  binary-search, trees, graphs, backtracking, DP, heaps/intervals, linked-list…).
- **Next-problem recommendation (session start):**
  1. If any problems are **due** (due ≤ today), recommend the most-overdue.
  2. Else recommend a **new/unseen** problem from the user's **weakest concept**.
  Also surface the full "due today" list and a small stats summary.
- **Configurable** (a `config.json` or settings UI): initial interval steps,
  starting ease, daily new-problem count, and whether to bias new picks toward
  weak concepts. Sensible defaults ship; tuning is optional.

### 8. Storage (backend)
- `problems/` read-only at runtime (the library).
- `data/schedule.json`: `{ problems: {slug: sm2state}, concepts: {tag: mastery} }`.
- `data/sessions/<timestamp>.json`: `{ slug, code, elapsed_ms, result, notes,
  test_summary, timestamp }` — append-only; this is the automated, richer
  successor to `03_Coding/coding_tracker.md` and the AI-analysis corpus.

## Data flow (one attempt)

1. Session start → GET `/next` → recommended problem + due list.
2. Open problem → GET `/problem/<slug>` → description, starter code, hints, tests meta.
3. User writes code, jots R.E.P.S. notes, timer runs.
4. `Run` → POST `/run` → stdout/stderr/runtime.
5. `Submit` → POST `/submit` → per-test results; if all pass and unaided → `clean`.
6. (Optional) `Show solution` → marks `peeked`.
7. Attempt finalized → POST `/attempt` → scheduler updates `schedule.json`, session
   log appended.

## Error handling

- Execution timeout → structured "Timed out after Ns" result, not a 500.
- Syntax/runtime errors in user code → captured traceback returned as data and
  shown in the results column; never crashes the server.
- Missing `entry_point` / wrong signature → clear message ("expected function
  `two_sum(nums, target)`").
- Corrupt/missing `schedule.json` → rebuild empty state and continue.
- Backend unreachable from frontend → visible error banner, no silent failure.

## Testing

- **Backend (pytest, TDD):**
  - `scheduler.py`: quality mapping, SM-2 interval/ease math, due selection,
    weak-concept selection, config overrides. Pure functions → thorough unit tests.
  - `executor.py`: correct results on passing code, failing tests, syntax error,
    runtime error, timeout, order-insensitive comparison.
  - `storage.py`: load problems, append session, update+persist schedule, recover
    from corrupt state.
- **Frontend:** lighter manual verification (load problem, run, submit, timer,
  reveal solution, notes persist).

## Milestones (Phase 1)

1. Backend skeleton + `executor.py` (run + run_tests) with pytest.
2. `storage.py` + problem JSON schema + 2–3 seed problems.
3. `scheduler.py` (SM-2 + concepts) with pytest.
4. FastAPI routes wiring executor/storage/scheduler.
5. Frontend: three-column layout, CodeMirror editor, results panel.
6. Timer + R.E.P.S. notes pane.
7. Session-start "what's next" screen.
8. Solutions/hints reveal + auto-`peeked`.
9. Seed to ~15–20 Blind 75 problems across the pattern sequence.
10. `reps.py` launcher + README.

## Phase 2 preview (not now)

- Claude API-powered interviewer chat (side panel) and an "analyze my session"
  pass over the collected notes/questions/timings/results, producing concrete
  "do this better next time" feedback and possibly new flashcards.
- Adds backend endpoints + a server-side `.env` key. No change to the Phase-1
  data model, execution model, or scheduler.
