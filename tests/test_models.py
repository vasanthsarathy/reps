from app.models import Problem, TestCase, Solution


def test_load_two_sum_from_file(two_sum_path):
    p = Problem.from_file(two_sum_path)
    assert p.slug == "two-sum"
    assert p.entry_point == "two_sum"
    assert p.compare == "exact"
    assert "hashing" in p.concepts
    assert isinstance(p.tests[0], TestCase)
    assert p.tests[0].args == [[2, 7, 11, 15], 9]
    assert p.tests[0].expected == [0, 1]
    assert isinstance(p.solutions[0], Solution)
    assert p.solutions[0].name


def test_compare_defaults_to_exact():
    p = Problem(
        slug="x", title="X", difficulty="Easy", concepts=[], source="Blind75",
        description="", entry_point="f", starter_code="def f():\n    pass\n", tests=[],
    )
    assert p.compare == "exact"
    assert p.hints == []
    assert p.solutions == []


def test_ml_fields_default_backward_compatible():
    # A pre-existing coding problem (no ML fields) gets safe defaults.
    p = Problem(
        slug="x", title="X", difficulty="Easy", concepts=[], source="Blind75",
        description="", entry_point="f", starter_code="def f():\n    pass\n",
    )
    assert p.track == "coding"
    assert p.libraries == []
    assert p.reference == ""
    assert p.random_tests is None
    assert p.banned == []
    assert p.rtol == 1e-4
    assert p.atol == 1e-6


def test_ml_fields_accepted():
    p = Problem(
        slug="softmax-stable", title="Softmax", difficulty="Easy",
        concepts=["activations"], source="ML-Impl", description="",
        entry_point="softmax", starter_code="def softmax(x):\n    pass\n",
        track="ml", libraries=["numpy"], reference="def softmax(x): return x",
        random_tests={"count": 5, "shapes": {"x": [8, 5]}, "dtype": "float32",
                      "range": [-5, 5], "seed": 0},
        banned=["sum"], compare="close", rtol=1e-5, atol=1e-8,
    )
    assert p.track == "ml"
    assert p.libraries == ["numpy"]
    assert p.compare == "close"
    assert p.random_tests["count"] == 5
    assert p.banned == ["sum"]
    assert p.rtol == 1e-5 and p.atol == 1e-8
