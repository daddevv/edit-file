"""
Pass 9 – Context-Aware Anchor Bounding Boxes
=============================================
The "lazy coding" phenomenon causes SLMs to correctly reproduce the first
and last lines of a target block while summarising the middle with comments
like ``# ... rest of code ...``.

This pass extracts the first and last *non-trivial* lines from old_text,
searches the file for them as unique anchors, and—if both are found and
are in the correct relative order—reconstructs the target block as
everything between (and including) those two anchors in the file.
"""
from __future__ import annotations

import re
from typing import Optional

from ..models import MatchResult, MatchStrategy
from .base import ReconcilerPass

# Lines that look like ellipsis / lazy placeholders.
_LAZY_RE = re.compile(
    r"^\s*("
    r"\.\.\."
    r"|#\s*(\.\.\..*|rest of.*|TODO.*|your code.*|more code.*|etc.*)"
    r"|pass"
    r")\s*$",
    re.IGNORECASE,
)


def _is_trivial(line: str) -> bool:
    return not line.strip() or bool(_LAZY_RE.match(line))


def _extract_anchors(old_text: str) -> tuple[Optional[str], Optional[str]]:
    """Return (first_significant_line, last_significant_line)."""
    lines = old_text.splitlines()
    first = next((l.rstrip() for l in lines if not _is_trivial(l)), None)
    last = next((l.rstrip() for l in reversed(lines) if not _is_trivial(l)), None)
    return first, last


def _find_line_index(file_lines: list[str], anchor: str) -> list[int]:
    """Return all 0-based line indices whose stripped content matches anchor."""
    target = anchor.strip()
    return [i for i, l in enumerate(file_lines) if l.rstrip() == anchor or l.strip() == target]


class AnchorBoundingPass(ReconcilerPass):
    label = "Anchor Bounding Box"
    strategy = MatchStrategy.ANCHOR
    pass_number = 9

    def find(self, content: str, old_text: str) -> Optional[MatchResult]:
        first_anchor, last_anchor = _extract_anchors(old_text)

        if not first_anchor or not last_anchor:
            return None

        if first_anchor == last_anchor:
            # Single-line block; anchors are identical—fall back rather than
            # risk an incorrect extraction.
            return None

        file_lines = content.splitlines(keepends=True)

        first_hits = _find_line_index(file_lines, first_anchor)
        last_hits = _find_line_index(file_lines, last_anchor)

        if not first_hits or not last_hits:
            return None

        # Find a pair where first_idx < last_idx with the smallest span.
        pairs = [
            (f, l)
            for f in first_hits
            for l in last_hits
            if l > f
        ]

        if not pairs:
            return None

        # Prefer the tightest span that still matches.
        line_start, line_end_inclusive = min(pairs, key=lambda p: p[1] - p[0])
        line_end = line_end_inclusive + 1  # exclusive

        char_start = sum(len(l) for l in file_lines[:line_start])
        char_end = sum(len(l) for l in file_lines[:line_end])

        # Penalise wide spans slightly.
        span = line_end - line_start
        query_lines = len(old_text.splitlines())
        ratio = min(query_lines, span) / max(query_lines, span)
        confidence = 0.75 * ratio  # max 0.75 – this is our most speculative pass

        return self._make_result(content, char_start, char_end, confidence=confidence)
