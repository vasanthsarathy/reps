"""Canonical concept tags and normalization for both tracks.

Existing tags were fragmented (e.g. "dp" vs "dynamic-programming", "two pointers"
vs "two-pointers"), which silently split the per-concept SM-2 mastery tracking.
`normalize_tag` maps the fragmented forms to canonical kebab-case; the combined
tag `"bfs-dfs"` is expanded to BOTH `"bfs"` and `"dfs"` by the migration (not here,
since that is a one-to-many mapping).
"""

_ALIASES = {
    "dp": "dynamic-programming",
    "two pointers": "two-pointers",
    "two-pointer": "two-pointers",
    "sliding window": "sliding-window",
    "bit manipulation": "bit-manipulation",
    "prefix sums": "prefix-sums",
    "bucket sort": "bucket-sort",
}

CANONICAL_TAGS = frozenset({
    # --- coding track ---
    "arrays", "hashing", "two-pointers", "fast-slow-pointers", "sliding-window",
    "prefix-sums", "binary-search", "stack", "linked-list", "trees", "bst", "trie",
    "heap", "two-heaps", "graphs", "bfs", "dfs", "topological-sort", "union-find",
    "backtracking", "recursion", "dynamic-programming", "greedy", "intervals",
    "matrix", "sorting", "bucket-sort", "divide-and-conquer", "bit-manipulation",
    "design", "math", "strings",
    # --- ml track ---
    "broadcasting", "tensors", "autodiff", "activations", "numerical-stability",
    "attention", "normalization", "loss-functions", "gradient-descent",
    "neural-networks", "linear-regression", "logistic-regression",
    "softmax-regression", "clustering", "dimensionality-reduction", "knn",
    "naive-bayes", "decision-trees", "metrics", "linear-algebra", "numpy-basics",
})


def normalize_tag(tag: str) -> str:
    """Map a possibly-fragmented tag to its canonical kebab-case form."""
    return _ALIASES.get(tag, tag)
