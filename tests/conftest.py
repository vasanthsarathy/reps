from pathlib import Path
import pytest
from app import config


@pytest.fixture
def two_sum_path() -> Path:
    return config.PROBLEMS_DIR / "two-sum.json"
