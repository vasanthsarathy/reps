<p align="center">
  <img src="assets/logo.svg" alt="reps — a spaced-repetition coding-interview gym" width="620">
</p>

<p align="center">
  <a href="#"><img alt="Python 3.14" src="https://img.shields.io/badge/python-3.14-3776AB?logo=python&logoColor=white"></a>
  <a href="#"><img alt="uv" src="https://img.shields.io/badge/managed%20by-uv-DE5FE9"></a>
  <a href="#"><img alt="tests" src="https://img.shields.io/badge/tests-204%20passing-2f9e8b"></a>
  <a href="#"><img alt="Blind 75" src="https://img.shields.io/badge/Blind%2075-75%2F75-5fd7bd"></a>
  <a href="#-license"><img alt="license: MIT" src="https://img.shields.io/badge/license-MIT-informational"></a>
</p>

<p align="center">
  A local, single-user <b>coding-interview gym</b>: three-column pad, live Python execution,<br>
  an adjustable timer, structured notes, and <b>spaced repetition</b> that tells you what to drill next.
</p>

---

## What it is

`reps` recreates the HackerRank / CoderPad interview experience on your own machine and wraps it in a
**spaced-repetition engine**, so every session opens with the *right* problem instead of a blank page.
It ships with all **75 Blind 75** problems and is built to make one thing effortless: **showing up and
doing reps under time pressure.**

```
┌──────────────────────────┬──────────────────────────┬──────────────────────────┐
│  PROBLEM                 │  EDITOR                  │  RESULTS                 │
│                          │                          │                          │
│  Description + examples  │  Python, syntax-         │  Run  ·  Submit          │
│  Progressive hints       │  highlighted             │  per-case ✓ / ✗          │
│  ▸ Show solution         │  (CodeMirror)            │  stdout / traceback      │
│                          │                          │                          │
│                          │                          │  R.E.P.S. notes          │
│                          │                          │  Restate · Examples ·    │
│                          │                          │  Plan · Step & speak     │
├──────────────────────────┴──────────────────────────┴──────────────────────────┤
│  ⏱  20:00  Start · Pause · Reset        Browse        What's next?              │
│  Rate this attempt:  [ Easy ] [ Good ] [ Hard ] [ Hint ] [ Peeked ]             │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Features

- 🧠 **Spaced repetition (SM-2 + concept tags).** Each session recommends a due review, or — if
  nothing's due — a fresh problem from your **weakest concept**. You never wonder what to do next.
- 🐍 **Live Python execution.** `Run` as a scratchpad, `Submit` against hidden tests. Real CPython in
  a timeout-isolated subprocess — real tracebacks, real timing.
- 🎨 **Syntax-highlighted editor** (CodeMirror), zero build step.
- ⏱ **Adjustable countdown timer** — visible, start / pause / reset, goes red past zero.
- 📝 **R.E.P.S. notes pane** — Restate · Examples · Plan · Step & speak — the freeze-protocol
  scaffold, captured with every attempt.
- 🎚 **Manual 5-level self-rating** — *Easy / Good / Hard / Hint / Peeked* — you grade the attempt,
  the scheduler does the rest.
- 📚 **All 75 Blind 75 problems** with original prompts, hidden tests, and reference solutions.
- 🔎 **Browse panel** — see every problem grouped by status (Due / New / Scheduled), search, and jump
  to any one anytime.
- 💾 **Everything is local files.** Your progress lives in `data/` — greppable, yours, gone the moment
  you delete it.

## Quick start

Requires [uv](https://docs.astral.sh/uv/) (it provisions Python 3.14 for you).

```bash
uv run python reps.py
```

Opens **http://127.0.0.1:8000** and loads your recommended next problem.

## The daily loop

1. **Open the app** — it picks your next problem (a due review, else a new one from your weakest
   concept). Or hit **Browse** to choose your own.
2. **Start the timer** and work the **R.E.P.S.** protocol out loud in the notes pane.
3. **`Run`** to scratch-test, **`Submit`** to check against the hidden tests.
4. **Rate the attempt** — one click — which records your progress and schedules the next review.

## How ratings drive scheduling

You pick one level after each problem; it maps to an SM-2 quality score:

| Level | Meaning | Effect |
|------|---------|--------|
| **Easy** | Solved, felt trivial | Passes → review gaps grow **fastest** over time |
| **Good** | Solved, normal effort | Passes → standard growth |
| **Hard** | Solved but a real struggle | Passes → gaps grow **slowest** |
| **Hint** | Needed a hint | Miss → back in **~2 days** |
| **Peeked** | Read the solution / gave up | Miss → back **tomorrow** |

Passing reviews climb a **1 → 3 → 7 day** ladder, then stretch by an ease factor that Easy nudges up
and Hard nudges down. Misses reset and resurface soon. Weak concepts (low clean-rate tags) surface
sooner in the "what's next" pick.

## Problem library

All **75 Blind 75** problems across every category — Arrays, Strings, Stack, Matrix, Binary Search,
Linked List, Trees & BST, Tries, Heap, Graphs, Dynamic Programming, and Bit Manipulation.

Each problem is a single JSON file in [`problems/`](problems/). **Adding one is a drop-in** — no code
change:

```jsonc
{
  "slug": "two-sum",
  "title": "Two Sum",
  "difficulty": "Easy",
  "concepts": ["hashing", "arrays"],
  "source": "Blind75",
  "description": "…markdown…",
  "entry_point": "two_sum",
  "starter_code": "def two_sum(nums, target):\n    pass\n",
  "compare": "exact",
  "tests": [ { "args": [[2,7,11,15], 9], "expected": [0,1] } ],
  "hints": ["…"],
  "solutions": [ { "name": "Hash map", "explanation": "…", "code": "…", "complexity": "Time O(n)" } ]
}
```

Problems run through a simple `entry_point(*args)` harness using plain built-in types, so trees are
level-order lists, graphs are adjacency lists, and design problems (Trie, median stream, …) are
modeled as operation sequences. A test guarantees **every reference solution passes its own hidden
tests**:

```bash
uv run pytest tests/test_problems_valid.py
```

## How it works

A thin **FastAPI** backend serves a static single-page frontend and does three things: runs your code
in a subprocess (with a timeout), stores problems + progress as files, and computes the schedule.

```
reps/
├── reps.py            # launcher: starts the server, opens your browser
├── app/
│   ├── main.py        # FastAPI routes
│   ├── executor.py    # runs user code / tests in a subprocess
│   ├── scheduler.py   # SM-2 + concept-mastery logic
│   ├── storage.py     # problems, schedule, session logs
│   └── frontend/      # index.html · style.css · app.js  (CodeMirror via CDN)
├── problems/          # the Blind 75 library — one JSON per problem
├── data/              # your progress (gitignored): schedule.json + sessions/
└── tests/             # pytest suite (backend logic + problem validity)
```

Executed code is **trusted** (it's your own code on your own machine), so the isolation is a
subprocess plus a hard timeout — no heavier sandbox.

## Your data

Progress persists to `data/` and survives restarts:

- `data/schedule.json` — per-problem SM-2 state + concept mastery
- `data/sessions/` — one file per attempt (your code, timing, and notes)

**Reset everything** (stop the server first):

```bash
rm -rf data            # full wipe — all problems back to "New"
rm data/schedule.json  # scheduling-only reset, keeps your attempt history
```

## Tests

```bash
uv run pytest
```

## Roadmap

- **Phase 2 — AI coach.** An interviewer chat plus an "analyze my session" pass over your captured
  notes, timings, and results to give concrete "do this better next time" feedback. Phase 1 already
  records everything it needs, so it slots in without rework.

## 📄 License

MIT — see [`LICENSE`](LICENSE).
