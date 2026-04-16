"""
Core data models for the edit-file reconciler.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class MatchStrategy(str, Enum):
    EXACT = "exact"
    WHITESPACE = "whitespace_normalized"
    INDENTATION = "relative_indentation"
    ESCAPE = "escape_unpacked"
    LEVENSHTEIN = "damerau_levenshtein"
    TOKEN_RATIO = "token_sort_set_ratio"
    SEMANTIC = "semantic_embedding"
    AST = "ast_structural"
    ANCHOR = "anchor_bounding"
    NONE = "none"


@dataclass
class MatchResult:
    """Represents a successful match found in the target file."""

    strategy: MatchStrategy
    start: int
    end: int
    matched_text: str          # The actual text from the file (not the LLM's query)
    confidence: float = 1.0    # 0.0 – 1.0; exact matches are always 1.0
    pass_number: int = 0


@dataclass
class EditResult:
    """Represents the outcome of an edit_file operation."""

    success: bool
    strategy_used: MatchStrategy = MatchStrategy.NONE
    pass_number: int = 0
    confidence: float = 0.0
    new_content: Optional[str] = None
    error: Optional[str] = None
    diagnostics: list[str] = field(default_factory=list)

    @classmethod
    def ok(
        cls,
        new_content: str,
        match: MatchResult,
        diagnostics: list[str] | None = None,
    ) -> "EditResult":
        return cls(
            success=True,
            strategy_used=match.strategy,
            pass_number=match.pass_number,
            confidence=match.confidence,
            new_content=new_content,
            diagnostics=diagnostics or [],
        )

    @classmethod
    def fail(cls, error: str, diagnostics: list[str] | None = None) -> "EditResult":
        return cls(
            success=False,
            error=error,
            diagnostics=diagnostics or [],
        )


@dataclass
class FileState:
    """Tracks the last-read state of a file for stale-read detection."""

    path: Path
    mtime: float
    size: int
    content: str