from __future__ import annotations

import pytest

import edit_file
from edit_file import EditFile, MatchStrategy, Reconciler
from edit_file.exceptions import StaleReadError
from edit_file.passes import ExactMatchPass


def test_public_package_imports() -> None:
    assert edit_file.__version__ == "0.1.0"
    assert edit_file.EditFile is EditFile
    assert edit_file.Reconciler is Reconciler
    assert MatchStrategy.EXACT.value == "exact"


def test_read_file_registers_snapshot_and_edit_updates_file(tmp_path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("value = 1\n", encoding="utf-8")
    editor = EditFile()

    assert editor.read_file(target) == "value = 1\n"
    result = editor.edit_file(target, "value = 1\n", "value = 2\n")

    assert result.success
    assert result.strategy_used == MatchStrategy.EXACT
    assert target.read_text(encoding="utf-8") == "value = 2\n"


def test_edit_requires_prior_read_by_default(tmp_path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("value = 1\n", encoding="utf-8")

    with pytest.raises(StaleReadError):
        EditFile().edit_file(target, "value = 1\n", "value = 2\n")


def test_stale_read_protection_rejects_external_change(tmp_path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("value = 1\n", encoding="utf-8")
    editor = EditFile()
    editor.read_file(target)
    target.write_text("value = 100\n", encoding="utf-8")

    with pytest.raises(StaleReadError):
        editor.edit_file(target, "value = 1\n", "value = 2\n")


def test_skip_stale_check_allows_edit_without_snapshot(tmp_path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("value = 1\n", encoding="utf-8")

    result = EditFile().edit_file(
        target,
        "value = 1\n",
        "value = 2\n",
        skip_stale_check=True,
    )

    assert result.success
    assert target.read_text(encoding="utf-8") == "value = 2\n"


def test_ambiguous_match_is_reported_as_failed_edit(tmp_path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("value = 1\nvalue = 1\n", encoding="utf-8")
    editor = EditFile(reconciler=Reconciler(passes=[ExactMatchPass()]))
    editor.read_file(target)

    result = editor.edit_file(target, "value = 1\n", "value = 2\n")

    assert not result.success
    assert "matched 2 locations" in (result.error or "")
    assert target.read_text(encoding="utf-8") == "value = 1\nvalue = 1\n"


def test_no_match_is_reported_as_failed_edit(tmp_path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("value = 1\n", encoding="utf-8")
    editor = EditFile(reconciler=Reconciler(passes=[ExactMatchPass()]))
    editor.read_file(target)

    result = editor.edit_file(target, "missing = True\n", "value = 2\n")

    assert not result.success
    assert "could not be located" in (result.error or "")
    assert target.read_text(encoding="utf-8") == "value = 1\n"
