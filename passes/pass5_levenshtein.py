"""
Pass 5 – Algorithmic Edit Distance (Damerau-Levenshtein)
=========================================================
Slides a window equal in line-count to old_text across the file and
computes the Damerau-Levenshtein similarity for each window.  The window
with the highest score above the threshold is accepted as the match.

The Damerau variant is preferred over plain Levenshtein because it counts
character *transpositions* as a single edit—a very common tokeniser
artefact in LLM outputs.

No external dependencies required; the algorithm is implemented in pure
Python with an O(M·N) DP table.
"""
from __future__ import annotations

from typing import Optional

from models import MatchResult, MatchStrategy
from passes.base import ReconcilerPass

_SIMILARITY_THRESHOLD = 0.90  # must be >= this to accept


def _damerau_levenshtein(s: str, t: str) -> int:
    """Return the Damerau-Levenshtein edit distance between s and t."""
    len_s, len_t = len(s), len(t)
    if len_s == 0:
        return len_t
    if len_t == 0:
        return len_s

    # d[i][j] = distance between s[:i] and t[:j]
    d = [[0] * (len_t + 1) for _ in range(len_s + 1)]
    for i in range(len_s + 1):
        d[i][0] = i
    for j in range(len_t + 1):
        d[0][j] = j

    for i in range(1, len_s + 1):
        for j in range(1, len_t + 1):
            cost = 0 if s[i - 1] == t[j - 1] else 1
            d[i][j] = min(
                d[i - 1][j] + 1,       # deletion
                d[i][j - 1] + 1,       # insertion
                d[i - 1][j - 1] + cost, # substitution
            )
            # Transposition
            if i > 1 and j > 1 and s[i - 1] == t[j - 2] and s[i - 2] == t[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + cost)

    return d[len_s][len_t]


def _similarity(s: str, t: str) -> float:
    dist = _damerau_levenshtein(s, t)
    max_len = max(len(s), len(t))
    if max_len == 0:
        return 1.0
    return 1.0 - dist / max_len


class LevenshteinPass(ReconcilerPass):
    label = "Damerau-Levenshtein Distance"
    strategy = MatchStrategy.LEVENSHTEIN
    pass_number = 5
    threshold: float = _SIMILARITY_THRESHOLD

    def find(self, content: str, old_text: str) -> Optional[MatchResult]:
        query = old_text.strip()
        if not query:
            return None

        # Skip if query is too long to be practical with O(M·N) DP.
        # Cap at 4000 chars to bound runtime.
        if len(query) > 4000 or len(content) > 80_000:
            return self._chunked_find(content, old_text)

        return self._chunked_find(content, old_text)

    def _chunked_find(self, content: str, old_text: str) -> Optional[MatchResult]:
        query_lines = old_text.strip().splitlines()
        n_query = len(query_lines)
        file_lines = content.splitlines(keepends=True)
        n_file = len(file_lines)

        if n_query == 0 or n_query > n_file:
            return None

        best_score = 0.0
        best_window: Optional[tuple[int, int]] = None

        query_str = "\n".join(query_lines)

        for i in range(n_file - n_query + 1):
            window_lines = file_lines[i : i + n_query]
            window_str = "".join(window_lines).rstrip()
            score = _similarity(query_str, window_str)
            if score > best_score:
                best_score = score
                best_window = (i, i + n_query)

        if best_score < self.threshold or best_window is None:
            return None

        line_start, line_end = best_window
        char_start = sum(len(l) for l in file_lines[:line_start])
        char_end = sum(len(l) for l in file_lines[:line_end])
        return self._make_result(content, char_start, char_end, confidence=best_score)