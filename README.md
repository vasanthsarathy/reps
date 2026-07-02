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
