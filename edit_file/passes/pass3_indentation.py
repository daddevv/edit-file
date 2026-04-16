"""
Pass 3 – Relative Indentation Preservation
===========================================
SLMs frequently generate code that is correctly structured internally but
"flushed left" or mis-indented relative to the target file's nested scope.

This pass strips the leading indentation from both the query and each line
of the file, finds a match in that de-indented space, then reports the
original (re-indented) block so the replacement can be applied correctly.
"""
from __future__ import annotations

import re
from typing import Optional

from ..exceptions import AmbiguousMatchError
from ..models import MatchResult, MatchStrategy
from .base import ReconcilerPass


def _strip_common_indent(text: str) -> tuple[str, str]:
    """
    Remove the common leading whitespace from all non-empty lines.
    Returns (stripped_text, common_prefix).
    """
    lines = text.splitlines(keepends=True)
    non_empty = [l for l in lines if l.strip()]
    if not non_empty:
        return text, ""

    # Find the shortest common indent.
    indents = [len(l) - len(l.lstrip()) for l in non_empty]
    common = min(indents)
    prefix = non_empty[0][:common] if common else ""

    stripped = "".join(
        (l[common:] if len(l) > common and l.strip() else l) for l in lines
    )
    return stripped, prefix


class RelativeIndentPass(ReconcilerPass):
    label = "Relative Indentation"
    strategy = MatchStrategy.INDENTATION
    pass_number = 3

    def find(self, content: str, old_text: str) -> Optional[MatchResult]:
        stripped_query, _ = _strip_common_indent(old_text)
        stripped_query = stripped_query.strip()

        if not stripped_query:
            return None

        # Slide a window of the same line-count over the file's lines.
        query_lines = stripped_query.splitlines()
        n_query = len(query_lines)
        file_lines = content.splitlines(keepends=True)
        n_file = len(file_lines)

        if n_query > n_file:
            return None

        matches: list[tuple[int, int]] = []  # (line_start, line_end) in file

        for i in range(n_file - n_query + 1):
            window = file_lines[i : i + n_query]
            stripped_window, _ = _strip_common_indent("".join(window))
            if stripped_window.strip() == stripped_query:
                matches.append((i, i + n_query))

        if not matches:
            return None
        if len(matches) > 1:
            raise AmbiguousMatchError(len(matches))

        line_start, line_end = matches[0]

        # Convert line indices to character offsets.
        char_start = sum(len(l) for l in file_lines[:line_start])
        char_end = sum(len(l) for l in file_lines[:line_end])
        return self._make_result(content, char_start, char_end, confidence=0.95)
