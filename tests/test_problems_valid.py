import pytest
from app import config, storage
from app.executor import run_tests, run_reference_tests, run_autograd_tests

PROBLEMS = storage.load_problems(config.PROBLEMS_DIR)
STATIC = [s for s, p in PROBLEMS.items() if p.tests]
REFERENCE = [s for s, p in PROBLEMS.items() if p.reference and p.random_tests]

ML_SOURCES = {"TensorPuzzles", "AutodiffPuzzles", "ClassicML", "ML-Impl"}


@pytest.mark.parametrize("slug", STATIC)
def test_static_reference_solution_passes_its_own_tests(slug):
    """Coding problems: the optimal solution must pass the problem's static tests."""
    p = PROBLEMS[slug]
    assert p.solutions, f"{slug} has no reference solution"
    ref = p.solutions[-1].code  # last = optimal
    r = run_tests(ref, p.entry_point, [t.model_dump() for t in p.tests], p.compare,
                  rtol=p.rtol, atol=p.atol)
    assert r["all_passed"], f"{slug} solution failed its own tests: {r}"


@pytest.mark.parametrize("slug", REFERENCE)
def test_reference_passes_its_own_random_tests(slug):
    """ML problems: the optimal solution must agree with the reference across the
    generated random tests (catches broken references, malformed random_tests specs,
    banned-token slips, and shape/serialization errors)."""
    p = PROBLEMS[slug]
    assert p.solutions, f"{slug} has no reference solution"
    code = p.solutions[-1].code
    if p.random_tests.get("mode") == "autograd":
        r = run_autograd_tests(code, p.entry_point, p.reference, p.random_tests,
                               rtol=p.rtol, atol=p.atol)
    else:
        r = run_reference_tests(code, p.entry_point, p.reference, p.random_tests,
                                p.compare, p.libraries, rtol=p.rtol, atol=p.atol)
    assert r["all_passed"], f"{slug} reference failed its own random tests: {r}"


@pytest.mark.parametrize("slug", list(PROBLEMS.keys()))
def test_problem_has_required_fields(slug):
    p = PROBLEMS[slug]
    assert p.concepts and p.hints and p.solutions
    assert p.entry_point in p.starter_code
    if p.track == "coding":
        assert p.source == "Blind75"
        assert p.tests, f"{slug} coding problem has no static tests"
    else:
        assert p.source in ML_SOURCES, f"{slug} unknown ML source {p.source!r}"
        assert p.reference and p.random_tests, f"{slug} ML problem missing reference/random_tests"
