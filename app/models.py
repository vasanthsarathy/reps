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
    compare: str = "exact"
    tests: list[TestCase] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    solutions: list[Solution] = Field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path) -> "Problem":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)
