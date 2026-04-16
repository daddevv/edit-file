from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

import pytest


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_text() -> Callable[[str, str], str]:
    def read(case: str, filename: str) -> str:
        return (FIXTURES / case / filename).read_text(encoding="utf-8")

    return read


@pytest.fixture
def copy_case_file(tmp_path: Path) -> Callable[[str, str], Path]:
    def copy(case: str, filename: str = "before.py") -> Path:
        source = FIXTURES / case / filename
        target = tmp_path / case / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return target

    return copy
