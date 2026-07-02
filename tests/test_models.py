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
