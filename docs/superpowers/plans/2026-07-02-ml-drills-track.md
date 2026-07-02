# ML Drills Track Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a second "ML implementation" track to `reps` — practicing turning math into NumPy/PyTorch code from a blank editor — seeded from Tensor-Puzzles, Autodiff-Puzzles, a classic-ML-from-scratch deck, and ~10 ML interview drills, scheduled by the existing SM-2 engine.

**Architecture:** Keep the FastAPI + subprocess-executor + vanilla-JS SPA. Extend the `Problem` schema with optional ML fields (done, Req 1). Upgrade the subprocess harness to (a) compare numpy/torch outputs with shape+`allclose`, (b) generate random inputs from a `random_tests` spec and derive `expected` by running a `reference`, (c) verify autodiff backward passes against `torch.autograd`, (d) reject `banned` tokens via an AST scan. Render Markdown+LaTeX in the left pane and add a Coding/ML deck toggle. Seed ~53 ML problems as JSON. All 76 coding problems keep working; SM-2 is untouched.

**Tech Stack:** Python 3.14, uv, FastAPI + uvicorn, pydantic v2, **numpy 2.5.0**, **torch 2.12.1+cpu**, pytest + httpx; CodeMirror 5, **marked**, **KaTeX** (all via CDN).

## Global Constraints

- Branch: `ml-drills`. Small, reviewable commits. Requirement 6 (tag normalization) is its **own isolated commit**.
- Run everything via `uv run`. Never bare `python`/`pip` (bare python is a MS Store stub).
- Python stays **3.14** (numpy 2.5.0 + torch 2.12.1 have cp314 Windows wheels — verified). Deps added via `uv add` only.
- **Do NOT change the SM-2 algorithm** (`app/scheduler.py` `quality_from_level`/`update_sm2`) or the content of the 76 existing coding problems (their tags get normalized in Req 6 only).
- All new `Problem` fields are optional and defaulted; every existing problem must validate unchanged.
- **Scope rule:** only executable, numerically-checkable drills. No conceptual flashcards. No plots/matplotlib. No auth/multiuser/deploy.
- Executed user code is trusted (user's own machine); isolation stays subprocess + timeout — no heavier sandbox.
- Problem descriptions/tests are ORIGINAL. Do NOT copy problem text or tests from LeetCode or deep-ml.com. Tensor-Puzzles/Autodiff-Puzzles specs (Sasha Rush, MIT-licensed) are ported as our own reference functions, not by vendoring their `lib.py`/torchtyping/chalk/hypothesis stack.
- After each requirement: run `uv run pytest -q` and report pass/fail before moving on.
- Frontend loads libraries from CDN — no bundler/build step.
- Deck decisions (locked): `bfs-dfs` → both `bfs` + `dfs`; "What's next?" recommends **within the active track**; SM-2 schedule is shared across tracks.

---

## File Structure

```
reps/
├── app/
│   ├── models.py          # Problem schema (Req 1 DONE: track, libraries, reference,
│   │                      #   random_tests, banned, rtol, atol)
│   ├── executor.py        # Req 2: tensor-aware harness, reference/random_tests,
│   │                      #   autograd check, banned-ops AST
│   ├── tags.py            # Req 6 NEW: CANONICAL_TAGS allow-list + normalize_tag()
│   ├── main.py            # Req 2: pass new fields to run_tests; Req 3: /problems track filter,
│   │                      #   /next?track=… ; storage.load_problems unchanged
│   ├── scheduler.py       # Req 3: recommend_next gains optional track filter (NO SM-2 change)
│   ├── storage.py         # unchanged
│   └── frontend/
│       ├── index.html     # Req 3: marked + KaTeX CDN; deck toggle in Browse
│       ├── app.js         # Req 3: renderMarkdown→marked+KaTeX; deck filter; tensor result render
│       └── style.css      # Req 3: deck-toggle + katex tweaks
├── problems/              # Req 4/5: ~53 new ML JSON files (existing 76 untouched except Req 6 tags)
├── docs/ML_TRACK.md       # Req 7: schema fields, the decks, how to author an ML drill
└── tests/
    ├── test_executor.py       # Req 2: comparator + reference-mode + banned + autograd tests
    ├── test_problems_valid.py # Req 2/4/5: reference-based problems self-check
    ├── test_tags.py           # Req 6: allow-list validation
    └── test_api.py            # Req 3: track filter on /problems and /next
```

---

## Task 2A: Executor — tensor-aware comparison

**Files:**
- Modify: `app/executor.py` (the `_HARNESS` string + a new comparison helper embedded in it)
- Test: `tests/test_executor.py`

**Interfaces:**
- Produces: the harness understands `compare="close"` and compares numpy `ndarray` / torch `Tensor`
  outputs by **shape then allclose** (`rtol`/`atol` from the payload). `"exact"` on arrays = same shape
  AND exact values (and exact dtype for numpy). NaN/inf mismatches yield `passed=False` with a clear
  message, never an exception. `got`/`expected` for arrays are stringified to `"shape=(…) dtype=… <vals>"`
  (truncated) so the JSON report stays serializable; on failure the row includes `max_abs_err`.
- Consumes: `run_tests(code, entry_point, tests, compare, timeout, rtol=1e-4, atol=1e-6)` — new
  `rtol`/`atol` kwargs threaded into the payload.

- [ ] **Step 1: Write failing tests** in `tests/test_executor.py`:

```python
from app.executor import run_tests

def test_close_compare_numpy_passes_within_tol():
    code = "import numpy as np\ndef f(x):\n    return np.asarray(x) * 2.0\n"
    tests = [{"args": [[1.0, 2.0]], "expected": [2.0, 4.0]}]
    r = run_tests(code, "f", tests, compare="close")
    assert r["all_passed"] is True

def test_close_compare_numpy_fails_and_reports_max_abs_err():
    code = "import numpy as np\ndef f(x):\n    return np.asarray(x) + 1.0\n"
    tests = [{"args": [[1.0, 2.0]], "expected": [2.0, 4.0]}]  # off by 1 on the 2nd
    r = run_tests(code, "f", tests, compare="close")
    assert r["all_passed"] is False
    assert r["results"][0].get("max_abs_err", 0) >= 0.9

def test_close_compare_shape_mismatch_is_fail_not_error():
    code = "import numpy as np\ndef f(x):\n    return np.asarray(x)[:1]\n"
    tests = [{"args": [[1.0, 2.0]], "expected": [1.0, 2.0]}]
    r = run_tests(code, "f", tests, compare="close")
    assert r["all_passed"] is False
    assert "shape" in str(r["results"][0]["got"]).lower() or "shape" in r["results"][0].get("note","").lower()

def test_close_compare_nan_is_fail_with_message():
    code = "import numpy as np\ndef f(x):\n    return np.asarray(x) * float('nan')\n"
    tests = [{"args": [[1.0]], "expected": [1.0]}]
    r = run_tests(code, "f", tests, compare="close")
    assert r["all_passed"] is False

def test_close_compare_torch_tensor():
    code = "import torch\ndef f(x):\n    return torch.tensor(x) + 1\n"
    tests = [{"args": [[1.0, 2.0]], "expected": [2.0, 3.0]}]
    r = run_tests(code, "f", tests, compare="close")
    assert r["all_passed"] is True

def test_exact_still_works_for_plain_values():
    code = "def f(a, b):\n    return a + b\n"
    r = run_tests(code, "f", [{"args": [2, 3], "expected": 5}], compare="exact")
    assert r["all_passed"] is True
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest tests/test_executor.py -k "close or exact_still" -v`
Expected: FAIL (numpy/torch not compared; `max_abs_err`/tolerant compare not implemented).

- [ ] **Step 3: Implement the comparison in `_HARNESS`.** Replace the `_norm`/compare logic in the
`_HARNESS` string in `app/executor.py` with a numeric-aware comparator. The harness runs in the venv
so it may `import numpy`/`import torch` lazily. Full new `_HARNESS`:

```python
_HARNESS = r'''
import json, sys, traceback

def _to_np(v):
    try:
        import numpy as np
    except Exception:
        return None
    try:
        import torch
        if isinstance(v, torch.Tensor):
            return v.detach().cpu().numpy()
    except Exception:
        pass
    if isinstance(v, np.ndarray):
        return v
    return None

def _is_array(v):
    return _to_np(v) is not None

def _fmt(v):
    a = _to_np(v)
    if a is not None:
        flat = a.reshape(-1)
        head = ", ".join(f"{x:.4g}" for x in flat[:8].tolist())
        more = "…" if flat.size > 8 else ""
        return f"shape={tuple(a.shape)} dtype={a.dtype} [{head}{more}]"
    return v

def _compare(got, expected, mode, rtol, atol):
    """Return (passed, note, max_abs_err|None). Never raises."""
    import numpy as np
    ga, ea = _to_np(got), _to_np(expected)
    if ga is not None or ea is not None:
        if ga is None: ga = np.asarray(got)
        if ea is None: ea = np.asarray(expected)
        if ga.shape != ea.shape:
            return False, f"shape mismatch: got {tuple(ga.shape)} want {tuple(ea.shape)}", None
        gf, ef = ga.astype("float64", copy=False), ea.astype("float64", copy=False)
        with np.errstate(all="ignore"):
            diff = np.abs(gf - ef)
            mae = float(np.nanmax(diff)) if diff.size else 0.0
        if np.isnan(gf).any() and not np.isnan(ef).any():
            return False, "output contains NaN", mae
        if np.isinf(gf).any() and not np.isinf(ef).any():
            return False, "output contains inf", mae
        if mode == "close":
            ok = bool(np.allclose(gf, ef, rtol=rtol, atol=atol, equal_nan=True))
        else:  # exact on arrays
            ok = bool(ga.shape == ea.shape and (ga.dtype == ea.dtype) and np.array_equal(ga, ea))
        return ok, "", mae
    # plain python values
    if mode == "unordered" and isinstance(got, list) and isinstance(expected, list):
        try:
            g = sorted(got, key=lambda z: json.dumps(z, sort_keys=True))
            e = sorted(expected, key=lambda z: json.dumps(z, sort_keys=True))
            return g == e, "", None
        except TypeError:
            return got == expected, "", None
    if mode == "close" and isinstance(got, (int, float)) and isinstance(expected, (int, float)):
        return abs(got - expected) <= atol + rtol * abs(expected), "", abs(got - expected)
    return got == expected, "", None

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
    rtol = float(payload.get("rtol", 1e-4)); atol = float(payload.get("atol", 1e-6))
    results = []
    for t in payload["tests"]:
        row = {"args": _fmt(t["args"]) if False else t["args"]}
        try:
            got = fn(*t["args"])
            passed, note, mae = _compare(got, t["expected"], mode, rtol, atol)
            row["got"] = _fmt(got); row["expected"] = _fmt(t["expected"])
            row["passed"] = passed
            if note: row["note"] = note
            if (not passed) and mae is not None: row["max_abs_err"] = mae
        except Exception:
            row["got"] = traceback.format_exc().strip().splitlines()[-1]
            row["expected"] = _fmt(t.get("expected"))
            row["passed"] = False
        results.append(row)
    print(json.dumps({"results": results}))

_main()
'''
```

Then update the `run_tests` signature/payload to thread tolerances:

```python
def run_tests(code: str, entry_point: str, tests: list[dict],
              compare: str = "exact", timeout: float = 10.0,
              rtol: float = 1e-4, atol: float = 1e-6) -> dict:
    payload = json.dumps({"code": code, "entry_point": entry_point,
                          "tests": tests, "compare": compare,
                          "rtol": rtol, "atol": atol})
    # ... rest unchanged ...
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_executor.py -v`
Expected: PASS (all existing + new comparator tests).

- [ ] **Step 5: Full suite (regression)**

Run: `uv run pytest -q`  → all prior tests still pass (206+ new).

- [ ] **Step 6: Commit**

```bash
git add app/executor.py tests/test_executor.py
git commit -m "feat(ml): tensor-aware close/exact comparison in the executor harness"
```

---

## Task 2B: Executor — reference + random_tests generation

**Files:**
- Modify: `app/executor.py` (add `run_reference_tests(...)` + input generation embedded in a harness)
- Test: `tests/test_executor.py`

**Interfaces:**
- Produces: `run_reference_tests(code, entry_point, reference, random_tests, compare, libraries,
  timeout=10.0, rtol=1e-4, atol=1e-6) -> dict` with the same result shape as `run_tests`
  (`{results, passed, total, all_passed, error, timed_out, runtime_ms}`). Each result row carries the
  generated input **shapes** (not the full arrays), `passed`, and `max_abs_err`/`note` on failure.
  Input generation: seed `numpy.random.default_rng(seed)`; for each name→shape in `random_tests["shapes"]`
  build an array of that shape with `dtype` in `random_tests["dtype"]` (default float32) filled uniformly
  in `random_tests["range"]` (default [-1,1]); if `dtype` is an int type, use integers in range. If
  `libraries` includes `"torch"` (and not numpy), pass `torch.tensor(...)` inputs; else numpy arrays.
  Run `reference` to get `expected`, run the user `entry_point`, compare with the Task-2A comparator.
- Consumes: the `_compare`/`_fmt` helpers from Task 2A (same harness style).

- [ ] **Step 1: Write failing tests**:

```python
from app.executor import run_reference_tests

SOFTMAX_REF = "import numpy as np\ndef softmax(x):\n    x=x-x.max(axis=-1,keepdims=True)\n    e=np.exp(x)\n    return e/e.sum(axis=-1,keepdims=True)\n"
RT = {"count": 5, "shapes": {"x": [4, 3]}, "dtype": "float32", "range": [-5, 5], "seed": 0}

def test_reference_correct_solution_passes():
    r = run_reference_tests(SOFTMAX_REF, "softmax", SOFTMAX_REF, RT, "close", ["numpy"])
    assert r["all_passed"] is True and r["total"] == 5

def test_reference_wrong_solution_fails():
    wrong = "import numpy as np\ndef softmax(x):\n    e=np.exp(x)\n    return e/e.sum(axis=-1,keepdims=True)\n"  # no max-subtract → still correct math! use a truly wrong one:
    wrong = "import numpy as np\ndef softmax(x):\n    return np.exp(x)\n"  # unnormalized
    r = run_reference_tests(wrong, "softmax", SOFTMAX_REF, RT, "close", ["numpy"])
    assert r["all_passed"] is False
    assert any("max_abs_err" in row for row in r["results"])

def test_reference_torch_inputs():
    ref = "import torch\ndef f(x):\n    return x.relu()\n"
    rt = {"count": 3, "shapes": {"x": [5]}, "dtype": "float32", "range": [-2, 2], "seed": 1}
    r = run_reference_tests(ref, "f", ref, rt, "close", ["torch"])
    assert r["all_passed"] is True
```

- [ ] **Step 2: Run to verify fail** — `uv run pytest tests/test_executor.py -k reference -v` → FAIL (ImportError: run_reference_tests).

- [ ] **Step 3: Implement `run_reference_tests`.** Add a second harness string `_REF_HARNESS` and the
Python wrapper. The harness receives `{code, entry_point, reference, random_tests, compare, libraries,
rtol, atol}` on stdin, generates inputs, runs reference + user, compares. Reuse `_to_np/_fmt/_compare`
by defining them once in a shared `_COMPARE_SRC` string prepended to both harnesses:

```python
_COMPARE_SRC = r'''
import json, sys, traceback
# (paste the _to_np, _is_array, _fmt, _compare functions from Task 2A here)
'''

_REF_HARNESS = _COMPARE_SRC + r'''
def _gen_inputs(rng, spec, use_torch):
    import numpy as np
    lo, hi = spec.get("range", [-1, 1])
    dtype = spec.get("dtype", "float32")
    args = []
    for name, shape in spec["shapes"].items():
        shape = tuple(shape)
        if "int" in dtype:
            a = rng.integers(int(lo), int(hi) + 1, size=shape).astype(dtype)
        else:
            a = (rng.random(size=shape) * (hi - lo) + lo).astype(dtype)
        if use_torch:
            import torch
            args.append(torch.tensor(a))
        else:
            args.append(a)
    return args

def _main():
    import numpy as np
    payload = json.loads(sys.stdin.read())
    spec = payload["random_tests"]
    use_torch = "torch" in payload.get("libraries", []) and "numpy" not in payload.get("libraries", [])
    mode = payload.get("compare", "close")
    rtol = float(payload.get("rtol", 1e-4)); atol = float(payload.get("atol", 1e-6))
    uns, rns = {}, {}
    try:
        exec(payload["reference"], rns)
        exec(payload["code"], uns)
    except Exception:
        print(json.dumps({"harness_error": "Error while loading code:\n" + traceback.format_exc()})); return
    ref = rns.get(payload["entry_point"]); usr = uns.get(payload["entry_point"])
    if not callable(ref) or not callable(usr):
        print(json.dumps({"harness_error": f"Missing function {payload['entry_point']!r}."})); return
    rng = np.random.default_rng(spec.get("seed", 0))
    results = []
    for _ in range(spec.get("count", 10)):
        args = _gen_inputs(rng, spec, use_torch)
        shapes = {k: list(np.asarray(_to_np(a) if _to_np(a) is not None else a).shape) for k, a in zip(spec["shapes"], args)}
        row = {"args": shapes}
        try:
            expected = ref(*[a.clone() if hasattr(a, "clone") else a.copy() for a in args])
            got = usr(*[a.clone() if hasattr(a, "clone") else a.copy() for a in args])
            passed, note, mae = _compare(got, expected, mode, rtol, atol)
            row["got"] = _fmt(got); row["expected"] = _fmt(expected); row["passed"] = passed
            if note: row["note"] = note
            if (not passed) and mae is not None: row["max_abs_err"] = mae
        except Exception:
            row["got"] = traceback.format_exc().strip().splitlines()[-1]; row["passed"] = False
        results.append(row)
    print(json.dumps({"results": results}))

_main()
'''
```

Wrapper mirrors `run_tests` (subprocess, timeout, parse last stdout line, `harness_error` handling,
`all_passed = passed == total and total > 0`). Refactor `run_tests`'s `_HARNESS` to also be
`_COMPARE_SRC + <loop>` so the comparator is defined once (DRY).

- [ ] **Step 4: Run to verify pass** — `uv run pytest tests/test_executor.py -v` → PASS.
- [ ] **Step 5: Full suite** — `uv run pytest -q` → no regressions.
- [ ] **Step 6: Commit**

```bash
git add app/executor.py tests/test_executor.py
git commit -m "feat(ml): reference + random_tests input generation in the executor"
```

---

## Task 2C: Executor — banned-ops AST check

**Files:** Modify `app/executor.py`; Test `tests/test_executor.py`.

**Interfaces:**
- Produces: `check_banned(code: str, banned: list[str]) -> str | None` — returns a message naming the
  first offending token if the user code references any banned name/attribute, else `None`. Detects
  bare names (`sum(...)`), attribute access (`x.view(...)` → bans `"view"`), and dotted calls
  (`np.dot` → bans `"np.dot"` or `"dot"`). Pure-Python AST, no execution.
- The reference-based and static runners call `check_banned` first when `banned` is non-empty and, if it
  returns a message, short-circuit to `{"results": [], "passed": 0, "total": 0, "all_passed": False,
  "error": "Banned: " + msg, "timed_out": False, "runtime_ms": 0}`.

- [ ] **Step 1: Failing tests**:

```python
from app.executor import check_banned

def test_banned_bare_name_detected():
    assert "sum" in (check_banned("def f(x):\n    return sum(x)\n", ["sum"]) or "")

def test_banned_attribute_detected():
    assert "view" in (check_banned("def f(x):\n    return x.view(-1)\n", ["view"]) or "")

def test_banned_dotted_detected():
    assert (check_banned("import numpy as np\ndef f(x):\n    return np.dot(x, x)\n", ["np.dot"]) or "")

def test_not_banned_returns_none():
    assert check_banned("def f(x):\n    return x + x\n", ["sum", "view"]) is None
```

- [ ] **Step 2: Run → FAIL** (`ImportError: check_banned`).
- [ ] **Step 3: Implement** in `app/executor.py`:

```python
import ast

def check_banned(code: str, banned: list[str]) -> str | None:
    if not banned:
        return None
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None  # a syntax error surfaces later at exec time
    bare = {b for b in banned if "." not in b}
    dotted = {b for b in banned if "." in b}
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in bare:
            hits.append(node.id)
        if isinstance(node, ast.Attribute) and node.attr in bare:
            hits.append(node.attr)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            full = f"{node.value.id}.{node.attr}"
            if full in dotted:
                hits.append(full)
    if hits:
        return f"use of disallowed token {sorted(set(hits))[0]!r}"
    return None
```

Wire it into `run_tests` and `run_reference_tests`: at the top, `msg = check_banned(code, banned)` and
short-circuit if set. Add a `banned: list[str] = None` kwarg to both (default `None` → no check).

- [ ] **Step 4: Run → PASS.**  **Step 5: Full suite** → no regressions.
- [ ] **Step 6: Commit** — `git commit -m "feat(ml): AST-based banned-ops enforcement"`.

---

## Task 2D: Executor — autograd backward-pass check + wire fields through /submit

**Files:** Modify `app/executor.py` (add `run_autograd_tests`), `app/main.py` (route dispatch);
Test `tests/test_executor.py`, `tests/test_api.py`.

**Interfaces:**
- Produces: `run_autograd_tests(code, entry_point, forward, random_tests, timeout=10.0, rtol=1e-4,
  atol=1e-6) -> dict`. The problem's `reference` holds a `forward(x)` (torch). The harness: seed;
  generate a random input `x` (float32, requires_grad); run `forward(x)`, backprop a random upstream
  gradient `g` (`torch.autograd.grad(out, x, grad_outputs=g)`) to get the true `dx`; call the user's
  `entry_point(x, g)` (documented signature: takes the input and upstream grad, returns `dx`); compare
  with `_compare` in `"close"` mode. Result shape identical to `run_tests`.
- `app/main.py` `submit()` chooses the runner by problem fields: if `problem.random_tests` and
  `problem.source == "AutodiffPuzzles"` (or `problem.compare == "close"` with an autograd marker
  `random_tests.get("mode") == "autograd"`) → `run_autograd_tests`; elif `problem.reference` and
  `problem.random_tests` → `run_reference_tests`; else → `run_tests`. All pass `problem.banned`,
  `problem.rtol`, `problem.atol`.

- [ ] **Step 1: Failing tests**:

```python
from app.executor import run_autograd_tests

RELU_FWD = "import torch\ndef forward(x):\n    return x.relu()\n"
RT = {"count": 4, "shapes": {"x": [6]}, "dtype": "float32", "range": [-2, 2], "seed": 0, "mode": "autograd"}

def test_autograd_correct_grad_passes():
    # user returns g * (x > 0)
    user = "import torch\ndef relu_backward(x, g):\n    return g * (x > 0).to(g.dtype)\n"
    r = run_autograd_tests(user, "relu_backward", RELU_FWD, RT)
    assert r["all_passed"] is True

def test_autograd_wrong_grad_fails():
    user = "import torch\ndef relu_backward(x, g):\n    return g\n"  # ignores the mask
    r = run_autograd_tests(user, "relu_backward", RELU_FWD, RT)
    assert r["all_passed"] is False
```

And in `tests/test_api.py` a dispatch test (uses the client fixture) confirming a reference-based ML
problem posted to `/submit` returns per-case results (add one tiny ML problem file under a tmp
`problems` dir, or assert dispatch via a monkeypatched loader — keep it to the existing client fixture
by adding a seeded ML problem in Task 5 and asserting `/submit` on it returns `all_passed`).

- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement `run_autograd_tests`** with a torch harness:

```python
_AUTOGRAD_HARNESS = _COMPARE_SRC + r'''
def _main():
    import numpy as np, torch
    payload = json.loads(sys.stdin.read())
    spec = payload["random_tests"]
    rtol = float(payload.get("rtol", 1e-4)); atol = float(payload.get("atol", 1e-6))
    fns, uns = {}, {}
    try:
        exec(payload["forward"], fns); exec(payload["code"], uns)
    except Exception:
        print(json.dumps({"harness_error": "Error while loading code:\n" + traceback.format_exc()})); return
    fwd = fns.get("forward"); usr = uns.get(payload["entry_point"])
    if not callable(fwd) or not callable(usr):
        print(json.dumps({"harness_error": "Missing forward or entry_point."})); return
    rng = np.random.default_rng(spec.get("seed", 0))
    lo, hi = spec.get("range", [-2, 2]); shape = tuple(next(iter(spec["shapes"].values())))
    results = []
    for _ in range(spec.get("count", 5)):
        xa = (rng.random(shape) * (hi - lo) + lo).astype("float32")
        x = torch.tensor(xa, requires_grad=True)
        out = fwd(x)
        g = torch.tensor((rng.random(tuple(out.shape)) * 2 - 1).astype("float32"))
        true_dx, = torch.autograd.grad(out, x, grad_outputs=g, retain_graph=False)
        row = {"args": {"x": list(shape)}}
        try:
            got = usr(torch.tensor(xa), torch.tensor(g.detach().numpy()))
            passed, note, mae = _compare(got, true_dx.detach(), "close", rtol, atol)
            row["got"] = _fmt(got); row["expected"] = _fmt(true_dx.detach()); row["passed"] = passed
            if note: row["note"] = note
            if (not passed) and mae is not None: row["max_abs_err"] = mae
        except Exception:
            row["got"] = traceback.format_exc().strip().splitlines()[-1]; row["passed"] = False
        results.append(row)
    print(json.dumps({"results": results}))
_main()
'''
```

Wrapper mirrors the others. Then update `app/main.py` `submit()` to dispatch (see Interfaces).

- [ ] **Step 4: Run → PASS.**  **Step 5: Full suite** → no regressions.
- [ ] **Step 6: Commit** — `git commit -m "feat(ml): torch.autograd backward-pass checking + /submit dispatch"`.

---

## Task 3: Frontend — Markdown+LaTeX, tensor results, deck toggle

**Files:** Modify `app/frontend/index.html`, `app/frontend/app.js`, `app/frontend/style.css`,
`app/main.py` (`/problems?track=`, `/next?track=`), `app/scheduler.py` (`recommend_next(..., track=None)`),
`tests/test_api.py`.

**Interfaces:**
- `recommend_next(problems, schedule, today, config, track=None)` — when `track` is set, only consider
  problems whose dict has `"track" == track`. Default `None` = all. **No SM-2 change.**
- `GET /api/next?track=ml` and `GET /api/problems` items include `"track"`. `list_problems` adds `track`.
- Frontend: `renderMarkdown` replaced by `marked.parse` + KaTeX auto-render (inline `$…$`, block `$$…$$`);
  results renderer shows `got`/`expected` strings + `max_abs_err`/`note`; a Coding/ML toggle in the
  Browse header filters `browseItems` by `track` and sets the active track used by `openBrowse`/`goNext`.

- [ ] **Step 1 (backend TDD): failing test** in `tests/test_api.py`:

```python
def test_problems_include_track(client):
    items = client.get("/api/problems").json()
    assert all("track" in it for it in items)

def test_next_track_filter(client):
    # with no ML problems seeded in the fixture, ml track → nothing recommended
    out = client.get("/api/next?track=ml").json()
    assert out["reason"] in {"new", "review", "done"}
```

- [ ] **Step 2: Run → FAIL** (no `track` key / param).
- [ ] **Step 3: Backend** — add `track` to each item in `list_problems`; add `track: str | None = None`
query param to `next_problem` and pass to `recommend_next`; add the `track` filter at the top of
`recommend_next` (`problems = [p for p in problems if track is None or p.get("track") == track]`).
- [ ] **Step 4: Run → PASS.**
- [ ] **Step 5: Frontend** — in `index.html` `<head>` add (mirroring the CodeMirror CDN lines):

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
```

Add a deck toggle to the Browse header in `index.html`:
```html
<div id="deck-toggle">
  <button class="deck active" data-track="">All</button>
  <button class="deck" data-track="coding">Coding</button>
  <button class="deck" data-track="ml">ML</button>
</div>
```

In `app.js` replace `renderMarkdown` with:
```javascript
function renderMarkdown(md) {
  const html = window.marked ? marked.parse(md || "") : (md || "");
  return html;
}
function typesetMath(el) {
  if (window.renderMathInElement) {
    renderMathInElement(el, {
      delimiters: [{left: "$$", right: "$$", display: true},
                   {left: "$", right: "$", display: false}],
      throwOnError: false,
    });
  }
}
```
and in `loadProblem`, after setting `#problem-desc` innerHTML, call `typesetMath($("#problem-desc"))`.
Add an `activeTrack` variable (default `""`); wire `#deck-toggle button` clicks to set it, re-filter
Browse, and use it in `goNext` (`/next?track=` + activeTrack) and the initial load. Update the results
renderer to print `got`/`expected`/`max_abs_err`/`note` (they're now strings). Add `.deck`/`.deck.active`
+ KaTeX spacing to `style.css`.

- [ ] **Step 6: Full suite** → no regressions. Manual: `uv run uvicorn app.main:app --port 8000`; a
seeded ML problem (after Task 5) renders LaTeX; deck toggle filters.
- [ ] **Step 7: Commit** — `git commit -m "feat(ml): markdown+LaTeX rendering, tensor results, deck toggle"`.

---

## Task 4: Seed content — Tensor-Puzzles, Autodiff-Puzzles, Classic-ML

**Files:** Create `problems/*.json` (ML track); `docs/ML_TRACK.md`.

**Interfaces:** Each new problem obeys the schema; `test_problems_valid.py` (extended in this task)
loads every problem and, for reference-based ones, runs the reference against its own `random_tests`
and asserts all pass — catching broken references. Authored in parallel batches (disjoint slug sets),
each batch self-validating its own files via `run_reference_tests`/`run_autograd_tests`.

- [ ] **Step 1: Extend `tests/test_problems_valid.py`** to cover reference-based problems:

```python
@pytest.mark.parametrize("slug", [s for s, p in PROBLEMS.items() if p.reference and p.random_tests])
def test_reference_passes_its_own_random_tests(slug):
    p = PROBLEMS[slug]
    from app.executor import run_reference_tests, run_autograd_tests
    if p.random_tests.get("mode") == "autograd":
        r = run_autograd_tests(p.solutions[-1].code, p.entry_point, p.reference, p.random_tests,
                               rtol=p.rtol, atol=p.atol)
    else:
        r = run_reference_tests(p.solutions[-1].code, p.entry_point, p.reference, p.random_tests,
                                p.compare, p.libraries, rtol=p.rtol, atol=p.atol)
    assert r["all_passed"], (slug, r)
```

Run: `uv run pytest tests/test_problems_valid.py -q` → still green (no ML problems yet).

- [ ] **Step 2: Author Tensor-Puzzles (21)** `source:"TensorPuzzles", track:"ml", libraries:["torch"]`,
`compare:"close"`, with `banned` per the README (no `view`, `sum`, `take`, `squeeze`, `tensor`, `arange`
unless provided, etc.). Each: `reference` = the puzzle's nested-loop `_spec` translated to a correct
function; `random_tests` = small integer tensors of the spec's shapes; `hints` = "1 line, broadcasting
only"; `solutions` = a known 1-line solution. Slugs: `tp-ones, tp-sum, tp-outer, tp-diag, tp-eye,
tp-triu, tp-cumsum, tp-diff, tp-vstack, tp-roll, tp-flip, tp-compress, tp-pad-to, tp-sequence-mask,
tp-bincount, tp-scatter-add, tp-flatten, tp-linspace, tp-heaviside, tp-repeat, tp-bucketize`.
Validate each with the self-check snippet; commit.

- [ ] **Step 3: Author Autodiff-Puzzles** `source:"AutodiffPuzzles", track:"ml", libraries:["torch"]`,
`compare:"close"`, `random_tests` with `"mode":"autograd"`. `reference` = `forward(x)`; user implements
`<op>_backward(x, g)`. Cover elementwise (relu, sigmoid, tanh, exp, log), reductions (sum, mean,
softmax), matmul/linear. Slugs: `ad-relu, ad-sigmoid, ad-tanh, ad-exp, ad-log, ad-sum, ad-mean,
ad-softmax, ad-matmul, ad-linear`. hints = chain rule; solutions = analytic grad. Self-check via
`run_autograd_tests`; commit.

- [ ] **Step 4: Author Classic-ML (~12)** `source:"ClassicML", track:"ml", libraries:["numpy"]`,
`compare:"close"`, ORIGINAL text (do NOT copy deep-ml). Slugs: `cml-linreg-normal-eq, cml-linreg-gd,
cml-logistic-regression, cml-kmeans-step, cml-pca, cml-knn-classify, cml-standardize, cml-train-test-split,
cml-classification-metrics, cml-sigmoid-bce, cml-gini-split, cml-naive-bayes, cml-softmax-regression,
cml-confusion-matrix` (pick ~12). LaTeX statements. Self-check; commit.

- [ ] **Step 5: Write `docs/ML_TRACK.md`** — the new schema fields, the three source decks + the ~10
implementation drills, how to author a new ML drill (the template), and the note that deep-ml.com stays
an external companion (not scraped). Commit.

- [ ] **Step 6: Full validation** — `uv run pytest tests/test_problems_valid.py -q` → every reference
passes its own random tests. `uv run pytest -q` → no regressions on the 76 coding problems.

---

## Task 5: Seed the 10 ML implementation drills

**Files:** Create `problems/*.json` (`source:"ML-Impl", track:"ml"`).

**Interfaces:** Same schema/self-check as Task 4. `compare:"close"`, `reference`+`random_tests`, LaTeX
statement, from-scratch `starter_code` stub.

- [ ] **Step 1: Author the 10** in priority order, slugs: `softmax-stable` (numpy), `activations-forward`
(relu/sigmoid/tanh, numpy), `cross-entropy-from-logits` (numpy), `layernorm-forward` (numpy),
`linreg-gd-step` (numpy; reference math from `../02_Math_to_Code/drill_01_gradient_descent.py`),
`mlp-forward` (numpy), `mlp-backward` (numpy), `self-attention` (numpy) + `self-attention-torch` (torch),
`causal-self-attention` (torch), `kmeans-step` (numpy). Each: LaTeX description, `# TODO` stub,
`reference` = correct impl, `random_tests`, `compare:"close"`.
- [ ] **Step 2: Wrong-answer test** — add to `tests/test_executor.py` a test that a softmax WITHOUT the
max-subtraction on extreme inputs, or an attention missing `1/√d`, is marked FAIL by
`run_reference_tests` against the correct reference. (Concretely: feed `range:[50,60]` logits so the
naive version overflows/differs.)
- [ ] **Step 3: Validate + full suite** — `uv run pytest -q` green; every reference self-checks.
- [ ] **Step 4: Commit** — `git commit -m "feat(ml): seed 10 ML implementation drills"`.

---

## Task 6: Normalize concept tags (ISOLATED COMMIT)

**Files:** Create `app/tags.py`; Modify `problems/*.json` (tag values only); Create `tests/test_tags.py`.

**Interfaces:**
- Produces: `app.tags.CANONICAL_TAGS` (frozenset) and `normalize_tag(tag: str) -> str` mapping the
  fragmented forms to canonical kebab-case.

- [ ] **Step 1: Create `app/tags.py`** with the mapping (from the confirmed decisions):

```python
_ALIASES = {
    "dp": "dynamic-programming", "dynamic-programming": "dynamic-programming",
    "two pointers": "two-pointers", "two-pointer": "two-pointers", "two-pointers": "two-pointers",
    "sliding window": "sliding-window", "sliding-window": "sliding-window",
    "bit manipulation": "bit-manipulation", "bit-manipulation": "bit-manipulation",
    "prefix sums": "prefix-sums", "bucket sort": "bucket-sort",
}
# bfs-dfs expands to BOTH bfs and dfs (handled in the migration script, not here)
CANONICAL_TAGS = frozenset({
    # coding
    "arrays","hashing","two-pointers","fast-slow-pointers","sliding-window","prefix-sums",
    "binary-search","stack","linked-list","trees","bst","trie","heap","two-heaps","graphs",
    "bfs","dfs","topological-sort","union-find","backtracking","recursion","dynamic-programming",
    "greedy","intervals","matrix","sorting","bucket-sort","divide-and-conquer","bit-manipulation",
    "design","math","strings",
    # ml
    "broadcasting","autodiff","activations","numerical-stability","attention","normalization",
    "loss-functions","gradient-descent","neural-networks","linear-regression","logistic-regression",
    "softmax-regression","clustering","dimensionality-reduction","knn","naive-bayes","decision-trees",
    "metrics","linear-algebra","tensors",
})
def normalize_tag(tag: str) -> str:
    return _ALIASES.get(tag, tag)
```

- [ ] **Step 2: Migration** — a one-off script normalizes every `problems/*.json` `concepts`: map via
`normalize_tag`, and expand any `"bfs-dfs"` into both `"bfs"` and `"dfs"` (dedup, preserve order).
Run it, then `git diff --stat` to confirm only tag values changed.
- [ ] **Step 3: Create `tests/test_tags.py`**:

```python
import glob, json
from app.tags import CANONICAL_TAGS

def test_all_problem_tags_are_canonical():
    bad = {}
    for f in glob.glob("problems/*.json"):
        p = json.load(open(f, encoding="utf-8"))
        off = [t for t in p["concepts"] if t not in CANONICAL_TAGS]
        if off: bad[p["slug"]] = off
    assert not bad, bad
```

- [ ] **Step 4: Run** `uv run pytest tests/test_tags.py -q` → PASS (fix any stragglers by adding the
canonical tag or correcting the problem). Full suite → green.
- [ ] **Step 5: Commit (ISOLATED)** — `git commit -m "chore: normalize concept tags to canonical kebab-case"`
(this commit touches ONLY `app/tags.py`, `problems/*.json` tag values, and `tests/test_tags.py`).

---

## Task 7: Final verification + docs

- [ ] **Step 1** — full suite `uv run pytest -q`: comparator tests, reference-self-check across all ML
problems, wrong-answer FAIL, banned-ops rejection, autograd check (right passes / wrong fails), zero
regressions on the 76 coding problems. Report counts.
- [ ] **Step 2 — manual smoke**: `uv run python reps.py`; switch to ML deck; open `softmax-stable` and
`self-attention`; confirm LaTeX renders; submit a correct solution (all pass) and an incorrect one
(fails with max-abs-err); confirm the attempt is recorded (schedule.json / sessions written).
- [ ] **Step 3** — ensure `docs/ML_TRACK.md` is complete. Commit any docs polish.

---

## Self-Review

**Spec coverage:** Req1 schema → DONE (pre-plan). Req2 executor: 2A close/exact tensor compare, 2B
reference+random_tests, 2C banned-ops, 2D autograd + /submit dispatch + numpy/torch install (done).
Req3 frontend marked+KaTeX + tensor results + deck toggle → Task 3 (+ backend track filter). Req4a/b/c
content → Task 4 (+ reference self-check test). Req5 10 drills → Task 5 (+ wrong-answer test). Req6 tag
normalization isolated commit + allow-list test → Task 6. Verification suite + ML_TRACK.md → Tasks 4/5/7.
Non-goals (no plots, no conceptual cards, no SM-2 change, no auth) respected. All requirements mapped.

**Placeholder scan:** No TBD/"handle edge cases". Content tasks (4/5) list exact slugs + sources +
libraries + compare mode + the self-check gate; each problem is mechanical given the schema + the worked
`_compare` harness, and guarded by `test_problems_valid.py`. Harness code is complete in 2A–2D.

**Type consistency:** `run_tests`/`run_reference_tests`/`run_autograd_tests` all return
`{results, passed, total, all_passed, error, timed_out, runtime_ms}`; result rows use `args, got,
expected, passed, note?, max_abs_err?`. `_compare(got, expected, mode, rtol, atol) -> (passed, note, mae)`
and `_fmt`/`_to_np` are shared via `_COMPARE_SRC`. `check_banned(code, banned) -> str|None`.
`recommend_next(..., track=None)`. `normalize_tag`/`CANONICAL_TAGS` in `app/tags.py`. Consistent across tasks.
