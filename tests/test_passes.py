from __future__ import annotations

import pytest

from edit_file.exceptions import AmbiguousMatchError
from edit_file.models import MatchStrategy
from edit_file.passes import (
    ASTStructuralPass,
    AnchorBoundingPass,
    EscapeUnpackPass,
    ExactMatchPass,
    LevenshteinPass,
    RelativeIndentPass,
    SemanticEmbeddingPass,
    TokenRatioPass,
    WhitespaceNormPass,
)


PASS_CASES = [
    ("pass1_exact", ExactMatchPass, MatchStrategy.EXACT, 1, 1.0, False),
    ("pass2_whitespace", WhitespaceNormPass, MatchStrategy.WHITESPACE, 2, 0.98, True),
    ("pass3_indentation", RelativeIndentPass, MatchStrategy.INDENTATION, 3, 0.95, False),
    ("pass4_escape", EscapeUnpackPass, MatchStrategy.ESCAPE, 4, 0.92, False),
    ("pass5_levenshtein", LevenshteinPass, MatchStrategy.LEVENSHTEIN, 5, 0.90, False),
    ("pass6_token", TokenRatioPass, MatchStrategy.TOKEN_RATIO, 6, 0.88, False),
    ("pass8_ast", ASTStructuralPass, MatchStrategy.AST, 8, 0.93, False),
    ("pass9_anchor", AnchorBoundingPass, MatchStrategy.ANCHOR, 9, 0.50, False),
]


@pytest.mark.parametrize(
    ("case", "pass_cls", "strategy", "pass_number", "min_confidence", "strip_expected"),
    PASS_CASES,
)
def test_pass_finds_expected_fixture(
    fixture_text,
    case: str,
    pass_cls,
    strategy: MatchStrategy,
    pass_number: int,
    min_confidence: float,
    strip_expected: bool,
) -> None:
    content = fixture_text(case, "before.py")
    old_text = fixture_text(case, "old.txt")
    expected_match = fixture_text(case, "expected_match.txt")
    if strip_expected:
        expected_match = expected_match.rstrip("\n")

    result = pass_cls().find(content, old_text)

    assert result is not None
    assert result.strategy == strategy
    assert result.pass_number == pass_number
    assert min_confidence <= result.confidence <= 1.0
    assert result.matched_text == expected_match
    assert content[result.start : result.end] == expected_match


def test_pass1_exact_returns_none_for_missing_text() -> None:
    assert ExactMatchPass().find("alpha\nbeta\n", "gamma\n") is None


def test_pass1_exact_raises_for_duplicate_text() -> None:
    with pytest.raises(AmbiguousMatchError):
        ExactMatchPass().find("alpha\nbeta\nalpha\n", "alpha\n")


def test_pass2_whitespace_raises_for_duplicate_normalized_text() -> None:
    with pytest.raises(AmbiguousMatchError):
        WhitespaceNormPass().find("alpha   beta\nalpha beta\n", "alpha beta\n")


def test_pass4_escape_returns_none_when_no_escape_information_is_added() -> None:
    assert EscapeUnpackPass().find("plain text\n", "plain text\n") is None


def test_pass5_levenshtein_rejects_low_similarity() -> None:
    content = "def compute():\n    return 42\n"
    old_text = "class CompletelyDifferent:\n    pass\n"
    assert LevenshteinPass().find(content, old_text) is None


def test_pass6_token_rejects_unrelated_tokens() -> None:
    content = "alpha beta gamma\n"
    old_text = "quantum zeppelin xylophone\n"
    assert TokenRatioPass().find(content, old_text) is None


def test_pass8_ast_rejects_invalid_query_syntax() -> None:
    content = "def area(width, height):\n    return width * height\n"
    assert ASTStructuralPass().find(content, "def area(:\n") is None


def test_pass8_ast_rejects_duplicate_structural_matches() -> None:
    content = (
        "def repeated():\n"
        "    return 1\n"
        "\n"
        "def repeated():\n"
        "    return 1\n"
    )
    old_text = "def repeated():\n    return 1\n"
    assert ASTStructuralPass().find(content, old_text) is None


def test_pass9_anchor_rejects_identical_anchors() -> None:
    content = "setup()\nwork()\nteardown()\n"
    assert AnchorBoundingPass().find(content, "setup()\n") is None


def test_pass9_anchor_rejects_reversed_anchors() -> None:
    content = "def run():\n    setup()\n    teardown()\n"
    old_text = "    teardown()\n    # ... rest of code ...\ndef run():\n"
    assert AnchorBoundingPass().find(content, old_text) is None


@pytest.mark.integration
@pytest.mark.semantic
def test_pass7_semantic_uses_real_cached_model(fixture_text) -> None:
    pytest.importorskip("sentence_transformers")

    content = fixture_text("pass7_semantic", "before.py")
    old_text = fixture_text("pass7_semantic", "old.txt")
    expected_match = fixture_text("pass7_semantic", "expected_match.txt")

    result = SemanticEmbeddingPass().find(content, old_text)
    if result is None:
        pytest.skip("sentence-transformers/all-MiniLM-L6-v2 is not cached locally")

    assert result.strategy == MatchStrategy.SEMANTIC
    assert result.pass_number == 7
    assert result.confidence >= 0.82
    assert result.matched_text == expected_match
