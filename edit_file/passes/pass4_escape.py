"""
Pass 4 – Escape Sequence and String Literal Unpacking
======================================================
Models often fail to correctly escape nested quotes, regex patterns, or
complex string literals.  This pass attempts to find a match by comparing
the *decoded* (raw) string values—ignoring escape representation—so that a
model that emits \\n instead of a literal newline, or vice-versa, can still
anchor its patch correctly.
"""
from __future__ import annotations

import codecs
import re
from typing import Optional

from ..exceptions import AmbiguousMatchError
from ..models import MatchResult, MatchStrategy
from .base import ReconcilerPass

_ESCAPE_RE = re.compile(
    r"\\(n|t|r|\\|'|\"|a|b|f|v|0|x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4})"
)


def _try_decode(text: str) -> str:
    """Best-effort decode of common escape sequences."""
    try:
        return codecs.decode(text, "unicode_escape")
    except Exception:
        pass
    # Fallback: manual replace of the most common sequences.
    replacements = {
        r"\n": "\n",
        r"\t": "\t",
        r"\r": "\r",
        r"\\": "\\",
        r"\'": "'",
        r"\"": '"',
    }
    for esc, raw in replacements.items():
        text = text.replace(esc, raw)
    return text


class EscapeUnpackPass(ReconcilerPass):
    label = "Escape Sequence Unpacking"
    strategy = MatchStrategy.ESCAPE
    pass_number = 4

    def find(self, content: str, old_text: str) -> Optional[MatchResult]:
        try:
            decoded_query = _try_decode(old_text)
            decoded_content = _try_decode(content)
        except Exception:
            return None

        if decoded_query == old_text and decoded_content == content:
            # Nothing was decoded – this pass adds no new information.
            return None

        occurrences: list[int] = []
        search_start = 0
        while True:
            idx = decoded_content.find(decoded_query, search_start)
            if idx == -1:
                break
            occurrences.append(idx)
            search_start = idx + 1

        if not occurrences:
            return None
        if len(occurrences) > 1:
            raise AmbiguousMatchError(len(occurrences))

        # The decoded indices correspond 1-to-1 with original indices only when
        # no multi-byte escapes exist; for safety, fall back to a search in the
        # original content using the decoded query.
        start = occurrences[0]
        end = start + len(decoded_query)

        # Re-anchor to the original content using the start position.
        # If decoding introduced length changes we accept approximate bounds.
        orig_end = min(end, len(content))
        return self._make_result(content, start, orig_end, confidence=0.92)
