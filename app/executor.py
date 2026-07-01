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
