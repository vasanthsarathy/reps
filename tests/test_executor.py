from app.executor import run, run_tests, run_reference_tests, run_autograd_tests, check_banned


def test_banned_bare_name_detected():
    assert "sum" in (check_banned("def f(x):\n    return sum(x)\n", ["sum"]) or "")


def test_banned_attribute_detected():
    assert "view" in (check_banned("def f(x):\n    return x.view(-1)\n", ["view"]) or "")


def test_banned_dotted_detected():
    assert (check_banned("import numpy as np\ndef f(x):\n    return np.dot(x, x)\n", ["np.dot"]) or "")


def test_not_banned_returns_none():
    assert check_banned("def f(x):\n    return x + x\n", ["sum", "view"]) is None


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

def test_close_compare_numpy_scalar_float32_passes_within_tol():
    code = "import numpy as np\ndef f(x):\n    return np.float32(sum(x))\n"
    tests = [{"args": [[1.0, 2.0, 3.0]], "expected": 6.0}]
    r = run_tests(code, "f", tests, compare="close")
    assert r["all_passed"] is True

def test_close_compare_numpy_scalar_float32_fails_and_reports_max_abs_err():
    code = "import numpy as np\ndef f(x):\n    return np.float32(sum(x))\n"
    tests = [{"args": [[1.0, 2.0, 3.0]], "expected": 5.0}]  # off by 1.0 > 0.9
    r = run_tests(code, "f", tests, compare="close")
    assert r["all_passed"] is False
    assert r["results"][0].get("max_abs_err", 0) >= 0.9

def test_exact_compare_numpy_bool_scalar_passes():
    code = "import numpy as np\ndef f(a, b):\n    return np.array_equal(a, b)\n"
    tests = [{"args": [[1, 2, 3], [1, 2, 3]], "expected": True}]
    r = run_tests(code, "f", tests, compare="exact")
    assert r["all_passed"] is True
    assert r["error"] == ""

def test_exact_compare_numpy_bool_scalar_fails():
    code = "import numpy as np\ndef f(a, b):\n    return np.array_equal(a, b)\n"
    tests = [{"args": [[1, 2, 3], [1, 2, 4]], "expected": True}]
    r = run_tests(code, "f", tests, compare="exact")
    assert r["all_passed"] is False
    assert r["error"] == ""


SOFTMAX_REF = "import numpy as np\ndef softmax(x):\n    x=x-x.max(axis=-1,keepdims=True)\n    e=np.exp(x)\n    return e/e.sum(axis=-1,keepdims=True)\n"
RT = {"count": 5, "shapes": {"x": [4, 3]}, "dtype": "float32", "range": [-5, 5], "seed": 0}

def test_reference_correct_solution_passes():
    r = run_reference_tests(SOFTMAX_REF, "softmax", SOFTMAX_REF, RT, "close", ["numpy"])
    assert r["all_passed"] is True and r["total"] == 5

def test_reference_wrong_solution_fails():
    wrong = "import numpy as np\ndef softmax(x):\n    return np.exp(x)\n"  # unnormalized
    r = run_reference_tests(wrong, "softmax", SOFTMAX_REF, RT, "close", ["numpy"])
    assert r["all_passed"] is False
    assert any("max_abs_err" in row for row in r["results"])

def test_reference_torch_inputs():
    ref = "import torch\ndef f(x):\n    return x.relu()\n"
    rt = {"count": 3, "shapes": {"x": [5]}, "dtype": "float32", "range": [-2, 2], "seed": 1}
    r = run_reference_tests(ref, "f", ref, rt, "close", ["torch"])
    assert r["all_passed"] is True


def test_run_tests_short_circuits_on_banned_token():
    """Verify that run_tests returns immediately when banned token is detected."""
    code = "def f(x):\n    return sum(x)\n"
    tests = [{"args": [[1, 2]], "expected": 3}]
    r = run_tests(code, "f", tests, banned=["sum"])
    assert r["all_passed"] is False
    assert r["error"].startswith("Banned:")
    assert "sum" in r["error"]
    assert r["results"] == []
    assert r["total"] == 0


def test_run_reference_tests_short_circuits_on_banned_token():
    """Verify that run_reference_tests returns immediately when banned token is detected."""
    code = "def f(x):\n    return sum(x)\n"
    ref = "def f(x):\n    return sum(x)\n"
    rt = {"count": 1, "shapes": {"x": [2]}, "dtype": "int32", "range": [1, 2], "seed": 0}
    r = run_reference_tests(code, "f", ref, rt, banned=["sum"])
    assert r["all_passed"] is False
    assert r["error"].startswith("Banned:")
    assert "sum" in r["error"]
    assert r["results"] == []
    assert r["total"] == 0


RELU_FWD = "import torch\ndef forward(x):\n    return x.relu()\n"
AUTOGRAD_RT = {"count": 4, "shapes": {"x": [6]}, "dtype": "float32", "range": [-2, 2], "seed": 0, "mode": "autograd"}


def test_autograd_correct_grad_passes():
    # user returns g * (x > 0)
    user = "import torch\ndef relu_backward(x, g):\n    return g * (x > 0).to(g.dtype)\n"
    r = run_autograd_tests(user, "relu_backward", RELU_FWD, AUTOGRAD_RT)
    assert r["all_passed"] is True


def test_autograd_wrong_grad_fails():
    user = "import torch\ndef relu_backward(x, g):\n    return g\n"  # ignores the mask
    r = run_autograd_tests(user, "relu_backward", RELU_FWD, AUTOGRAD_RT)
    assert r["all_passed"] is False


def test_autograd_forward_exception_fails_gracefully():
    # forward() raises on every sampled input; this must not crash the whole
    # subprocess run (no JSON output) — each row should fail individually.
    bad_fwd = "def forward(x):\n    raise ValueError('boom')\n"
    user = "import torch\ndef relu_backward(x, g):\n    return g\n"
    r = run_autograd_tests(user, "relu_backward", bad_fwd, AUTOGRAD_RT)
    assert r["all_passed"] is False
    assert r["results"] != []
    assert r["error"] == ""
    assert all(row["passed"] is False for row in r["results"])
    assert any("ValueError" in row["got"] for row in r["results"])


def test_reference_scalar_const_arg():
    # random_tests.shapes with an int value passes a constant scalar arg (e.g. k).
    ref = "import numpy as np\ndef f(x, k):\n    return x * k\n"
    rt = {"count": 4, "shapes": {"x": [4], "k": 3}, "dtype": "float32", "range": [-2, 2], "seed": 0}
    from app.executor import run_reference_tests
    ok = run_reference_tests(ref, "f", ref, rt, "close", ["numpy"])
    assert ok["all_passed"] is True and ok["total"] == 4
    wrong = "import numpy as np\ndef f(x, k):\n    return x * (k + 1)\n"
    bad = run_reference_tests(wrong, "f", ref, rt, "close", ["numpy"])
    assert bad["all_passed"] is False


def test_reference_per_arg_dtype_and_range():
    # dtype/range may be dicts keyed by input name: float features + int labels.
    ref = "import numpy as np\ndef f(x, y):\n    return x.sum() + y.sum()\n"
    rt = {"count": 3, "shapes": {"x": [4], "y": [4]},
          "dtype": {"x": "float32", "y": "int64"},
          "range": {"x": [-1, 1], "y": [0, 2]}, "seed": 0}
    from app.executor import run_reference_tests
    r = run_reference_tests(ref, "f", ref, rt, "close", ["numpy"])
    assert r["all_passed"] is True and r["total"] == 3


def test_ml_wrong_softmax_without_maxsub_fails_on_extreme_logits():
    from app.executor import run_reference_tests
    ref = "import numpy as np\ndef softmax(x):\n    x = x - x.max(axis=-1, keepdims=True)\n    e = np.exp(x)\n    return e / e.sum(axis=-1, keepdims=True)\n"
    wrong = "import numpy as np\ndef softmax(x):\n    e = np.exp(x)\n    return e / e.sum(axis=-1, keepdims=True)\n"
    rt = {"count": 5, "shapes": {"x": [4, 5]}, "dtype": "float32", "range": [90, 100], "seed": 0}
    assert run_reference_tests(ref, "softmax", ref, rt, "close", ["numpy"])["all_passed"] is True
    assert run_reference_tests(wrong, "softmax", ref, rt, "close", ["numpy"])["all_passed"] is False


def test_ml_wrong_attention_missing_scale_fails():
    from app.executor import run_reference_tests
    ref = ("import numpy as np\ndef attn(Q, K, V):\n    d = Q.shape[-1]\n    s = Q @ K.T / np.sqrt(d)\n"
           "    s = s - s.max(axis=-1, keepdims=True)\n    w = np.exp(s); w = w / w.sum(axis=-1, keepdims=True)\n    return w @ V\n")
    wrong = ("import numpy as np\ndef attn(Q, K, V):\n    s = Q @ K.T\n"
             "    s = s - s.max(axis=-1, keepdims=True)\n    w = np.exp(s); w = w / w.sum(axis=-1, keepdims=True)\n    return w @ V\n")
    rt = {"count": 5, "shapes": {"Q": [4, 8], "K": [4, 8], "V": [4, 8]}, "dtype": "float32", "range": [-2, 2], "seed": 0}
    assert run_reference_tests(ref, "attn", ref, rt, "close", ["numpy"])["all_passed"] is True
    assert run_reference_tests(wrong, "attn", ref, rt, "close", ["numpy"])["all_passed"] is False
