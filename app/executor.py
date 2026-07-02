from __future__ import annotations
import ast
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def check_banned(code: str, banned: list[str]) -> str | None:
    """Check if code uses any banned names/attributes.

    Returns a message naming the first offending token, or None if all clear.
    Detects bare names (sum(...)), attribute access (x.view(...)),
    and dotted calls (np.dot).
    """
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


_COMPARE_SRC = r'''
import json, sys, traceback, warnings

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
    if isinstance(v, (np.ndarray, np.generic)):
        return np.asarray(v)
    return None

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
        try:
            gf, ef = ga.astype("float64", copy=False), ea.astype("float64", copy=False)
        except (ValueError, TypeError):
            return False, "non-numeric array output", None
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore")
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
            note = "" if ok or ga.dtype == ea.dtype else f"dtype mismatch: got {ga.dtype} want {ea.dtype}"
            return ok, note, mae
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
'''

_HARNESS = _COMPARE_SRC + r'''
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
        row = {"args": t["args"]}
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
    print(json.dumps({"results": results}, default=str))

_main()
'''


def run_tests(code: str, entry_point: str, tests: list[dict],
              compare: str = "exact", timeout: float = 10.0,
              rtol: float = 1e-4, atol: float = 1e-6, banned: list[str] = None) -> dict:
    msg = check_banned(code, banned)
    if msg:
        return {"results": [], "passed": 0, "total": 0, "all_passed": False,
                "error": "Banned: " + msg, "timed_out": False, "runtime_ms": 0}
    payload = json.dumps({"code": code, "entry_point": entry_point,
                          "tests": tests, "compare": compare,
                          "rtol": rtol, "atol": atol})
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
        xa = (rng.random(shape) * (hi - lo) + lo).astype("float32")  # autograd inputs are always float32 (grads require float)
        x = torch.tensor(xa, requires_grad=True)
        row = {"args": {"x": list(shape)}}
        try:
            out = fwd(x)
            g = torch.tensor((rng.random(tuple(out.shape)) * 2 - 1).astype("float32"))
            true_dx, = torch.autograd.grad(out, x, grad_outputs=g, retain_graph=False)
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


def run_autograd_tests(code: str, entry_point: str, forward: str, random_tests: dict,
                       timeout: float = 10.0, rtol: float = 1e-4, atol: float = 1e-6) -> dict:
    payload = json.dumps({"code": code, "entry_point": entry_point, "forward": forward,
                          "random_tests": random_tests, "rtol": rtol, "atol": atol})
    total = random_tests.get("count", 5)
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "autograd_harness.py"
        harness.write_text(_AUTOGRAD_HARNESS, encoding="utf-8")
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, str(harness)], input=payload,
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return {"results": [], "passed": 0, "total": total,
                    "all_passed": False, "error": f"Timed out after {timeout:g}s",
                    "timed_out": True,
                    "runtime_ms": int((time.perf_counter() - start) * 1000)}
        runtime_ms = int((time.perf_counter() - start) * 1000)
        try:
            out = json.loads(proc.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            return {"results": [], "passed": 0, "total": total,
                    "all_passed": False,
                    "error": proc.stderr or "No output from test harness.",
                    "timed_out": False, "runtime_ms": runtime_ms}
        if "harness_error" in out:
            return {"results": [], "passed": 0, "total": total,
                    "all_passed": False, "error": out["harness_error"],
                    "timed_out": False, "runtime_ms": runtime_ms}
        results = out["results"]
        passed = sum(1 for r in results if r["passed"])
        return {"results": results, "passed": passed, "total": len(results),
                "all_passed": passed == len(results) and len(results) > 0,
                "error": "", "timed_out": False, "runtime_ms": runtime_ms}


def run_reference_tests(code: str, entry_point: str, reference: str, random_tests: dict,
                        compare: str = "close", libraries: list[str] | None = None,
                        timeout: float = 10.0, rtol: float = 1e-4, atol: float = 1e-6,
                        banned: list[str] = None) -> dict:
    msg = check_banned(code, banned)
    if msg:
        return {"results": [], "passed": 0, "total": 0, "all_passed": False,
                "error": "Banned: " + msg, "timed_out": False, "runtime_ms": 0}
    payload = json.dumps({"code": code, "entry_point": entry_point, "reference": reference,
                          "random_tests": random_tests, "compare": compare,
                          "libraries": libraries or [], "rtol": rtol, "atol": atol})
    total = random_tests.get("count", 10)
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "ref_harness.py"
        harness.write_text(_REF_HARNESS, encoding="utf-8")
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, str(harness)], input=payload,
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return {"results": [], "passed": 0, "total": total,
                    "all_passed": False, "error": f"Timed out after {timeout:g}s",
                    "timed_out": True,
                    "runtime_ms": int((time.perf_counter() - start) * 1000)}
        runtime_ms = int((time.perf_counter() - start) * 1000)
        try:
            out = json.loads(proc.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            return {"results": [], "passed": 0, "total": total,
                    "all_passed": False,
                    "error": proc.stderr or "No output from test harness.",
                    "timed_out": False, "runtime_ms": runtime_ms}
        if "harness_error" in out:
            return {"results": [], "passed": 0, "total": total,
                    "all_passed": False, "error": out["harness_error"],
                    "timed_out": False, "runtime_ms": runtime_ms}
        results = out["results"]
        passed = sum(1 for r in results if r["passed"])
        return {"results": results, "passed": passed, "total": len(results),
                "all_passed": passed == len(results) and len(results) > 0,
                "error": "", "timed_out": False, "runtime_ms": runtime_ms}
