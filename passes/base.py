"""
Abstract base class for all reconciler passes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from models import MatchResult, MatchStrategy


class ReconcilerPass(ABC):
    """
    Each pass in the 9-pass chain must implement this interface.

    Passes receive the raw file content and the LLM-supplied old_text.
    On success they return a MatchResult whose ``matched_text`` is the
    *actual* substring from the file—never the LLM's query—so the caller
    can perform a verbatim replacement that preserves original formatting.

    On failure they return None and the chain advances to the next pass.
    """

    #: Human-readable label used in diagnostics.
    label: str = "unnamed"
    strategy: MatchStrategy = MatchStrategy.NONE
    pass_number: int = 0

    @abstractmethod
    def find(self, content: str, old_text: str) -> Optional[MatchResult]:
        """
        Attempt to locate old_text within content.

        Returns a MatchResult on success, None if this pass cannot find a match.
        Must never raise—absorb internal errors and return None.
        """

    def _make_result(
        self,
        content: str,
        start: int,
        end: int,
        confidence: float = 1.0,
    ) -> MatchResult:
        """Helper to build a MatchResult from file-space indices."""
        return MatchResult(
            strategy=self.strategy,
            start=start,
            end=end,
            matched_text=content[start:end],
            confidence=confidence,
            pass_number=self.pass_number,
        )