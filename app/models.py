from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field


class TestCase(BaseModel):
    __test__ = False

    args: list[Any]
    expected: Any


class Solution(BaseModel):
    name: str
    explanation: str
    code: str
    complexity: str = ""


class Problem(BaseModel):
    slug: str
    title: str
    difficulty: str
    concepts: list[str]
    source: str
    description: str
    entry_point: str
    starter_code: str
    compare: str = "exact"  # "exact" | "unordered" | "close"
    tests: list[TestCase] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    solutions: list[Solution] = Field(default_factory=list)

    # --- ML track (all optional, backward compatible) ---
    track: str = "coding"  # "coding" | "ml"
    libraries: list[str] = Field(default_factory=list)  # e.g. ["numpy"], ["torch"]
    reference: str = ""  # reference-solution body; generates expected for random_tests
    random_tests: dict | None = None  # {count, shapes, dtype, range, seed, ...}
    banned: list[str] = Field(default_factory=list)  # AST-rejected names/attrs
    rtol: float = 1e-4  # tolerance for compare="close"
    atol: float = 1e-6

    @classmethod
    def from_file(cls, path: Path) -> "Problem":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)
