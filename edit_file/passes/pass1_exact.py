"""
Pass 1 – Exact Literal Match
============================
Performs a standard literal substring search.  If old_text appears exactly
once in the file the match is returned immediately (O(N)).  If it appears
more than once an AmbiguousMatchError is raised so the agent can provide a
more specific context block.
"""
from __future__ import annotations

from typing import Optional

from ..exceptions import AmbiguousMatchError
from ..models import MatchResult, MatchStrategy
from .base import ReconcilerPass


class ExactMatchPass(ReconcilerPass):
    label = "Exact Literal Match"
    strategy = MatchStrategy.EXACT
    pass_number = 1

    def find(self, content: str, old_text: str) -> Optional[MatchResult]:
        # Collect every occurrence so we can enforce uniqueness.
        occurrences: list[int] = []
        search_start = 0
        while True:
            idx = content.find(old_text, search_start)
            if idx == -1:
                break
            occurrences.append(idx)
            search_start = idx + 1  # allow overlapping detection

        if len(occurrences) == 0:
            return None

        if len(occurrences) > 1:
            raise AmbiguousMatchError(len(occurrences))

        start = occurrences[0]
        end = start + len(old_text)
        return self._make_result(content, start, end, confidence=1.0)
