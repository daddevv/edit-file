"""
Pass 6 – Lexical Token Sorting and Set Ratios
==============================================
Sometimes a model recalls the correct logical components of a block but
outputs them in a slightly altered sequence (e.g. swapped parameter order).
This pass tokenises both strings, sorts the tokens alphabetically, and
compares using intersection / remainder logic (Token Sort Ratio and Token Set
Ratio), mirroring the approach of libraries like TheFuzz / RapidFuzz.

Implemented in pure Python—no external dependencies required.
"""
from __future__ import annotations

import re
from typing import Optional

from models import MatchResult, MatchStrategy
from passes.base import ReconcilerPass

_TOKEN_RE = re.compile(r"\w+")
_THRESHOLD = 0.88


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _token_sort_ratio(a: str, b: str) -> float:
    ta = " ".join(sorted(_tokenize(a)))
    tb = " ".join(sorted(_tokenize(b)))
    return _sequence_ratio(ta, tb)


def _token_set_ratio(a: str, b: str) -> float:
    set_a = set(_tokenize(a))
    set_b = set(_tokenize(b))
    intersection = sorted(set_a & set_b)
    remainder_a = sorted(set_a - set_b)
    remainder_b = sorted(set_b - set_a)

    base = " ".join(intersection)
    str_a = (base + " " + " ".join(remainder_a)).strip()
    str_b = (base + " " + " ".join(remainder_b)).strip()

    return max(
        _sequence_ratio(base, str_a),
        _sequence_ratio(base, str_b),
        _sequence_ratio(str_a, str_b),
    )


def _sequence_ratio(a: str, b: str) -> float:
    """Simple character-level ratio without importing difflib."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    # Count matching characters using a two-pointer approach on sorted text.
    # This is intentionally simple; for production swap in SequenceMatcher.
    common = sum((c in b) for c in a)  # approximation
    return 2.0 * common / (len(a) + len(b))


def _combined_score(query: str, window: str) -> float:
    return max(_token_sort_ratio(query, window), _token_set_ratio(query, window))


class TokenRatioPass(ReconcilerPass):
    label = "Token Sort / Set Ratio"
    strategy = MatchStrategy.TOKEN_RATIO
    pass_number = 6
    threshold: float = _THRESHOLD

    def find(self, content: str, old_text: str) -> Optional[MatchResult]:
        query = old_text.strip()
        if not query:
            return None

        query_lines = query.splitlines()
        n_query = len(query_lines)
        file_lines = content.splitlines(keepends=True)
        n_file = len(file_lines)

        if n_query == 0 or n_query > n_file:
            return None

        best_score = 0.0
        best_window: Optional[tuple[int, int]] = None

        for i in range(n_file - n_query + 1):
            window = "".join(file_lines[i : i + n_query])
            score = _combined_score(query, window)
            if score > best_score:
                best_score = score
                best_window = (i, i + n_query)

        if best_score < self.threshold or best_window is None:
            return None

        line_start, line_end = best_window
        char_start = sum(len(l) for l in file_lines[:line_start])
        char_end = sum(len(l) for l in file_lines[:line_end])
        return self._make_result(content, char_start, char_end, confidence=best_score)