from __future__ import annotations

import json
import subprocess
import sys

import pytest

from edit_file.models import MatchStrategy


@pytest.mark.e2e
def test_cli_edit_json_updates_real_file(fixture_text, copy_case_file) -> None:
    target = copy_case_file("pass1_exact")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "edit_file.cli",
            "edit",
            str(target),
            "--old",
            fixture_text("pass1_exact", "old.txt"),
            "--new",
            fixture_text("pass1_exact", "replacement.txt"),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["success"] is True
    assert payload["strategy"] == MatchStrategy.EXACT.value
    assert payload["pass"] == 1
    assert target.read_text(encoding="utf-8") == fixture_text(
        "pass1_exact", "expected_after.py"
    )
