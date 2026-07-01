import pytest
from app import config, storage
from app.executor import run_tests

PROBLEMS = storage.load_problems(config.PROBLEMS_DIR)


@pytest.mark.parametrize("slug", list(PROBLEMS.keys()))
def test_reference_solution_passes_its_own_tests(slug):
    p = PROBLEMS[slug]
    assert p.solutions, f"{slug} has no reference solution"
    ref = p.solutions[-1].code  # last = optimal
    r = run_tests(ref, p.entry_point, [t.model_dump() for t in p.tests], p.compare)
    assert r["all_passed"], f"{slug} reference solution failed: {r}"


@pytest.mark.parametrize("slug", list(PROBLEMS.keys()))
def test_problem_has_required_fields(slug):
    p = PROBLEMS[slug]
    assert p.source == "Blind75"
    assert p.concepts and p.tests and p.hints
    assert p.entry_point in p.starter_code
