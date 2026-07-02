from app import focus

def test_get_group_all_is_none():
    assert focus.get_group("all") is None
    assert focus.get_group(None) is None

def test_matches_track_and_concepts():
    g = focus.get_group("coding-dp")
    assert focus.matches({"track": "coding", "concepts": ["dynamic-programming"]}, g)
    assert not focus.matches({"track": "coding", "concepts": ["graphs"]}, g)
    assert not focus.matches({"track": "ml", "concepts": ["dynamic-programming"]}, g)

def test_matches_sources():
    g = focus.get_group("ml-tensors")  # topic group defined by source
    assert focus.matches({"track": "ml", "source": "TensorPuzzles"}, g)
    assert not focus.matches({"track": "ml", "source": "ClassicML"}, g)

def test_matches_libraries_logic():
    # matches() still supports library criteria (used internally); test with a synthetic group
    g = {"track": "ml", "libraries": {"torch"}}
    assert focus.matches({"track": "ml", "libraries": ["torch"]}, g)
    assert not focus.matches({"track": "ml", "libraries": ["numpy"]}, g)

def test_ml_basics_group_by_concept():
    g = focus.get_group("ml-basics")
    assert focus.matches({"track": "ml", "concepts": ["numpy-basics"]}, g)
    assert not focus.matches({"track": "ml", "concepts": ["attention"]}, g)

def test_group_list_has_expected_ids():
    ids = {g["id"] for g in focus.group_list()}
    assert {"all", "coding", "ml", "ml-basics", "ml-tensors", "ml-classic", "ml-attention", "coding-dp"} <= ids
    # the old library-based groups are gone
    assert "ml-numpy" not in ids and "ml-torch" not in ids
