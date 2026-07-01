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
