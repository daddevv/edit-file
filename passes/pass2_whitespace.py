"""
Pass 2 – Whitespace Invariance and Normalization
=================================================
Collapses all contiguous whitespace (spaces, tabs, newlines) in both the
file content and old_text into single spaces, finds a unique match in that
normalised space, then maps the boundary indices back to the original string
so the replacement preserves the file's formatting exactly.
"""
from __future__ import annotations

import re
from typing import Optional

from exceptions import AmbiguousMatchError
from models import MatchResult, MatchStrategy
from passes.base import ReconcilerPass

_WS = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WS.sub(" ", text).strip()


def _build_index_map(original: str) -> list[int]:
    """
    Returns a list where index_map[i] is the position in *original* that
    corresponds to index i in the normalised string.
    """
    norm_to_orig: list[int] = []
    prev_was_ws = False
    started = False

    for orig_idx, ch in enumerate(original):
        is_ws = bool(_WS.match(ch))
        if is_ws:
            if not prev_was_ws and started:
                norm_to_orig.append(orig_idx)  # the single replacement space
            prev_was_ws = True
        else:
            norm_to_orig.append(orig_idx)
            prev_was_ws = False
            started = True

    return norm_to_orig


class WhitespaceNormPass(ReconcilerPass):
    label = "Whitespace Normalization"
    strategy = MatchStrategy.WHITESPACE
    pass_number = 2

    def find(self, content: str, old_text: str) -> Optional[MatchResult]:
        norm_content = _normalize(content)
        norm_query = _normalize(old_text)

        if not norm_query:
            return None

        # Collect occurrences in normalised space.
        occurrences: list[int] = []
        search_start = 0
        while True:
            idx = norm_content.find(norm_query, search_start)
            if idx == -1:
                break
            occurrences.append(idx)
            search_start = idx + 1

        if not occurrences:
            return None
        if len(occurrences) > 1:
            raise AmbiguousMatchError(len(occurrences))

        norm_start = occurrences[0]
        norm_end = norm_start + len(norm_query)

        # Map back to original string positions.
        index_map = _build_index_map(content)
        if norm_end > len(index_map):
            return None

        orig_start = index_map[norm_start]
        # norm_end - 1 gives the last character of the match; walk to the end
        # of that character in the original string.
        last_orig = index_map[norm_end - 1]

        # Extend to cover the full whitespace run after the last real char.
        orig_end = last_orig + 1
        while orig_end < len(content) and content[orig_end] in (" ", "\t"):
            orig_end += 1

        return self._make_result(content, orig_start, orig_end, confidence=0.98)