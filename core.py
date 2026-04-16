"""
High-level EditFile API
=======================
Provides read_file / edit_file operations with:

* stale-read detection (race-condition prevention)
* atomic writes (write-to-temp then rename)
* full reconciler integration

Typical agent workflow::

    editor = EditFile()

    # 1. Read the file (registers the snapshot).
    content = editor.read_file("mymodule.py")

    # 2. Apply an edit.
    result = editor.edit_file(
        path="mymodule.py",
        old_text="def foo():\\n    pass",
        new_text="def foo():\\n    return 42",
    )
    if not result.success:
        print("Edit failed:", result.error)
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

from exceptions import StaleReadError
from models import EditResult, FileState
from reconciler import Reconciler


class EditFile:
    """
    Stateful editor that tracks file snapshots for stale-read protection.

    Parameters
    ----------
    reconciler:
        Custom Reconciler instance.  Defaults to the standard 9-pass chain.
    encoding:
        File encoding (default: utf-8).
    """

    def __init__(
        self,
        reconciler: Optional[Reconciler] = None,
        encoding: str = "utf-8",
    ) -> None:
        self._reconciler = reconciler or Reconciler()
        self._encoding = encoding
        self._snapshots: dict[Path, FileState] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read_file(self, path: str | Path) -> str:
        """
        Read a file and register its current state for stale-read detection.
        Returns the file content as a string.
        """
        p = Path(path).resolve()
        stat = p.stat()
        content = p.read_text(encoding=self._encoding)
        self._snapshots[p] = FileState(
            path=p,
            mtime=stat.st_mtime,
            size=stat.st_size,
            content=content,
        )
        return content

    def edit_file(
        self,
        path: str | Path,
        old_text: str,
        new_text: str,
        *,
        skip_stale_check: bool = False,
    ) -> EditResult:
        """
        Replace old_text with new_text in the given file.

        Parameters
        ----------
        path:
            Path to the file to edit.
        old_text:
            The text block the agent believes exists in the file.
        new_text:
            The replacement text.
        skip_stale_check:
            Bypass the stale-read check.  Use with care.

        Returns
        -------
        EditResult
            On success: new_content is set and success=True.
            On failure: error message is set and success=False.
        """
        p = Path(path).resolve()
        diagnostics: list[str] = []

        # ── Stale-read guard ─────────────────────────────────────────────
        if not skip_stale_check:
            stale_error = self._check_stale(p)
            if stale_error:
                raise StaleReadError(str(path))

        # ── Read current content ─────────────────────────────────────────
        try:
            content = p.read_text(encoding=self._encoding)
        except OSError as exc:
            return EditResult.fail(f"Cannot read file: {exc}")

        # ── Run reconciler ───────────────────────────────────────────────
        try:
            new_content, match = self._reconciler.apply(content, old_text, new_text)
        except Exception as exc:
            return EditResult.fail(str(exc), diagnostics)

        # ── Atomic write ─────────────────────────────────────────────────
        try:
            self._atomic_write(p, new_content)
        except OSError as exc:
            return EditResult.fail(f"Write failed: {exc}", diagnostics)

        # Update snapshot so subsequent edits in the same session don't
        # immediately trip the stale-read guard.
        stat = p.stat()
        self._snapshots[p] = FileState(
            path=p,
            mtime=stat.st_mtime,
            size=stat.st_size,
            content=new_content,
        )

        return EditResult.ok(new_content, match, diagnostics)

    def forget(self, path: str | Path) -> None:
        """Remove the cached snapshot for a path."""
        self._snapshots.pop(Path(path).resolve(), None)

    def forget_all(self) -> None:
        """Clear all cached snapshots."""
        self._snapshots.clear()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _check_stale(self, path: Path) -> bool:
        """
        Return True if the file has changed since the last read_file call.
        Also returns True (conservatively) if the file has never been read.
        """
        snapshot = self._snapshots.get(path)
        if snapshot is None:
            # File was never read through this editor instance.
            return True
        try:
            stat = path.stat()
        except OSError:
            return True
        return stat.st_mtime != snapshot.mtime or stat.st_size != snapshot.size

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write content to path atomically via a temp file + rename."""
        dir_ = path.parent
        fd, tmp_path = tempfile.mkstemp(dir=dir_, prefix=".editfile_", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding=self._encoding) as fh:
                fh.write(content)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise