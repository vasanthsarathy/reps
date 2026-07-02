from app.executor import run, run_tests


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
