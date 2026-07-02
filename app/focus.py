"""Curated session-focus groups: named views over the problem set for the recommender."""

# Each group: id, label, and any of: track / concepts / libraries / sources (a problem matches a
# group if it satisfies ALL present criteria; concepts/libraries match if there is ANY overlap).
FOCUS_GROUPS = [
    {"id": "all", "label": "All problems"},
    {"id": "coding", "label": "Coding — Blind 75", "track": "coding"},
    {"id": "coding-arrays", "label": "Coding · Arrays & hashing", "track": "coding",
     "concepts": {"arrays", "hashing", "two-pointers", "sliding-window", "prefix-sums"}},
    {"id": "coding-dp", "label": "Coding · Dynamic programming", "track": "coding",
     "concepts": {"dynamic-programming"}},
    {"id": "coding-graphs", "label": "Coding · Graphs", "track": "coding",
     "concepts": {"graphs", "bfs", "dfs", "union-find", "topological-sort"}},
    {"id": "coding-trees", "label": "Coding · Trees & BST", "track": "coding",
     "concepts": {"trees", "bst", "trie"}},
    {"id": "coding-linked", "label": "Coding · Linked lists", "track": "coding",
     "concepts": {"linked-list", "fast-slow-pointers"}},
    {"id": "ml", "label": "ML — everything", "track": "ml"},
    {"id": "ml-linalg", "label": "ML · Linear algebra", "track": "ml", "concepts": {"linear-algebra"}},
    {"id": "ml-numpy", "label": "ML · NumPy from scratch", "track": "ml", "libraries": {"numpy"}},
    {"id": "ml-torch", "label": "ML · Tensors & PyTorch", "track": "ml", "libraries": {"torch"}},
    {"id": "ml-autodiff", "label": "ML · Autodiff / backprop", "track": "ml", "concepts": {"autodiff"}},
    {"id": "ml-attention", "label": "ML · Attention & LLMs", "track": "ml", "concepts": {"attention"}},
]

_BY_ID = {g["id"]: g for g in FOCUS_GROUPS}

def get_group(focus_id):
    """Return the group dict for an id, or None (== no filter / all)."""
    if not focus_id or focus_id == "all":
        return None
    return _BY_ID.get(focus_id)

def matches(problem: dict, group) -> bool:
    """problem is a dict with track/concepts/libraries/source. group is a FOCUS_GROUPS entry or None."""
    if group is None:
        return True
    if group.get("track") and problem.get("track", "coding") != group["track"]:
        return False
    if group.get("concepts") and not (set(problem.get("concepts", [])) & group["concepts"]):
        return False
    if group.get("libraries") and not (set(problem.get("libraries", [])) & group["libraries"]):
        return False
    if group.get("sources") and problem.get("source") not in group["sources"]:
        return False
    return True

def group_list():
    """[{id, label}] for the UI dropdown."""
    return [{"id": g["id"], "label": g["label"]} for g in FOCUS_GROUPS]
