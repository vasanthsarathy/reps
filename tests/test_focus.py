from app import focus

def test_get_group_all_is_none():
    assert focus.get_group("all") is None
    assert focus.get_group(None) is None

def test_matches_track_and_concepts():
    g = focus.get_group("coding-dp")
    assert focus.matches({"track": "coding", "concepts": ["dynamic-programming"]}, g)
    assert not focus.matches({"track": "coding", "concepts": ["graphs"]}, g)
    assert not focus.matches({"track": "ml", "concepts": ["dynamic-programming"]}, g)

def test_matches_libraries():
    g = focus.get_group("ml-torch")
    assert focus.matches({"track": "ml", "libraries": ["torch"]}, g)
    assert not focus.matches({"track": "ml", "libraries": ["numpy"]}, g)

def test_group_list_has_expected_ids():
    ids = {g["id"] for g in focus.group_list()}
    assert {"all", "coding", "ml", "ml-attention", "coding-dp"} <= ids
