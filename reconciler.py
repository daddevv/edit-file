"""
The Client-Side Reconciler
==========================
Runs the 9-pass Chain of Responsibility until a match is found.

Usage::

    from edit_file.reconciler import Reconciler

    r = Reconciler()
    match = r.find(content, old_text)   # returns MatchResult or raises
"""
from __future__ import annotations

from typing import Optional

from exceptions import NoMatchFoundError
from models import MatchResult
from passes import (AnchorBoundingPass, ASTStructuralPass, EscapeUnpackPass,
                    ExactMatchPass, LevenshteinPass, RelativeIndentPass,
                    SemanticEmbeddingPass, TokenRatioPass, WhitespaceNormPass)
from passes.base import ReconcilerPass

_DEFAULT_CHAIN: list[ReconcilerPass] = [
    ExactMatchPass(),
    WhitespaceNormPass(),
    RelativeIndentPass(),
    EscapeUnpackPass(),
    LevenshteinPass(),
    TokenRatioPass(),
    SemanticEmbeddingPass(),
    ASTStructuralPass(),
    AnchorBoundingPass(),
]


class Reconciler:
    """
    Runs each pass in sequence, short-circuiting on the first successful
    match.  Raises NoMatchFoundError if the chain is exhausted.

    Parameters
    ----------
    passes:
        Custom pass chain.  Defaults to the canonical 9-pass chain.
    min_confidence:
        Reject matches whose confidence is below this value even if a pass
        claims success.  Defaults to 0.0 (accept all).
    """

    def __init__(
        self,
        passes: Optional[list[ReconcilerPass]] = None,
        min_confidence: float = 0.0,
    ) -> None:
        self._passes = passes if passes is not None else list(_DEFAULT_CHAIN)
        self.min_confidence = min_confidence

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find(self, content: str, old_text: str) -> MatchResult:
        """
        Locate old_text within content using the reconciler chain.

        Returns the MatchResult from the first successful pass.
        Raises NoMatchFoundError if all passes fail.

        Note: AmbiguousMatchError and StaleReadError propagate unchanged.
        """
        diagnostics: list[str] = []

        for p in self._passes:
            try:
                result = p.find(content, old_text)
            except Exception:
                # Let AmbiguousMatchError / StaleReadError bubble up.
                raise

            if result is None:
                diagnostics.append(f"Pass {p.pass_number} ({p.label}): no match")
                continue

            if result.confidence < self.min_confidence:
                diagnostics.append(
                    f"Pass {p.pass_number} ({p.label}): match below confidence "
                    f"threshold ({result.confidence:.2f} < {self.min_confidence:.2f})"
                )
                continue

            diagnostics.append(
                f"Pass {p.pass_number} ({p.label}): matched "
                f"[{result.start}:{result.end}] confidence={result.confidence:.2f}"
            )
            result._diagnostics = diagnostics  # type: ignore[attr-defined]
            return result

        raise NoMatchFoundError(passes_tried=len(self._passes))

    def apply(self, content: str, old_text: str, new_text: str) -> tuple[str, MatchResult]:
        """
        Find old_text in content and replace it with new_text.

        Returns (new_content, match_result).
        """
        match = self.find(content, old_text)
        new_content = content[: match.start] + new_text + content[match.end :]
        return new_content, match