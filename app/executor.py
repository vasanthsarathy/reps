from __future__ import annotations
import json
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
