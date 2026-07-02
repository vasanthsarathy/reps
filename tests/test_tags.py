import glob
import json

from app.tags import CANONICAL_TAGS, normalize_tag


def test_all_problem_tags_are_canonical():
    """Every problem must use only canonical concept tags (kebab-case allow-list)."""
    bad = {}
    for f in glob.glob("problems/*.json"):
        p = json.load(open(f, encoding="utf-8"))
        off = [t for t in p["concepts"] if t not in CANONICAL_TAGS]
        if off:
            bad[p["slug"]] = off
    assert not bad, f"non-canonical tags: {bad}"


def test_normalize_tag_maps_fragmented_forms():
    assert normalize_tag("dp") == "dynamic-programming"
    assert normalize_tag("two pointers") == "two-pointers"
    assert normalize_tag("sliding window") == "sliding-window"
    assert normalize_tag("bit manipulation") == "bit-manipulation"
    assert normalize_tag("prefix sums") == "prefix-sums"
    assert normalize_tag("bucket sort") == "bucket-sort"
    # already-canonical tags pass through unchanged
    assert normalize_tag("hashing") == "hashing"
    assert normalize_tag("attention") == "attention"
