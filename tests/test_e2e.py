from __future__ import annotations

import pytest

from edit_file import EditFile, MatchStrategy, Reconciler
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


ISOLATED_CASES = [
    ("pass1_exact", ExactMatchPass, MatchStrategy.EXACT, 1),
    ("pass2_whitespace", WhitespaceNormPass, MatchStrategy.WHITESPACE, 2),
    ("pass3_indentation", RelativeIndentPass, MatchStrategy.INDENTATION, 3),
    ("pass4_escape", EscapeUnpackPass, MatchStrategy.ESCAPE, 4),
    ("pass5_levenshtein", LevenshteinPass, MatchStrategy.LEVENSHTEIN, 5),
    ("pass6_token", TokenRatioPass, MatchStrategy.TOKEN_RATIO, 6),
    ("pass8_ast", ASTStructuralPass, MatchStrategy.AST, 8),
    ("pass9_anchor", AnchorBoundingPass, MatchStrategy.ANCHOR, 9),
]


@pytest.mark.e2e
@pytest.mark.parametrize(("case", "pass_cls", "strategy", "pass_number"), ISOLATED_CASES)
def test_isolated_pass_edits_real_file(
    fixture_text,
    copy_case_file,
    case: str,
    pass_cls,
    strategy: MatchStrategy,
    pass_number: int,
) -> None:
    target = copy_case_file(case)
    editor = EditFile(reconciler=Reconciler(passes=[pass_cls()]))
    editor.read_file(target)

    result = editor.edit_file(
        target,
        old_text=fixture_text(case, "old.txt"),
        new_text=fixture_text(case, "replacement.txt"),
    )

    assert result.success, result.error
    assert result.strategy_used == strategy
    assert result.pass_number == pass_number
    assert target.read_text(encoding="utf-8") == fixture_text(case, "expected_after.py")


@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.semantic
def test_semantic_pass_edits_real_file_with_real_cached_model(fixture_text, copy_case_file) -> None:
    pytest.importorskip("sentence_transformers")

    semantic_pass = SemanticEmbeddingPass()
    content = fixture_text("pass7_semantic", "before.py")
    old_text = fixture_text("pass7_semantic", "old.txt")
    if semantic_pass.find(content, old_text) is None:
        pytest.skip("sentence-transformers/all-MiniLM-L6-v2 is not cached locally")

    target = copy_case_file("pass7_semantic")
    editor = EditFile(reconciler=Reconciler(passes=[semantic_pass]))
    editor.read_file(target)

    result = editor.edit_file(
        target,
        old_text=old_text,
        new_text=fixture_text("pass7_semantic", "replacement.txt"),
    )

    assert result.success, result.error
    assert result.strategy_used == MatchStrategy.SEMANTIC
    assert result.pass_number == 7
    assert target.read_text(encoding="utf-8") == fixture_text(
        "pass7_semantic", "expected_after.py"
    )


DEFAULT_CHAIN_CASES = [
    ("pass1_exact", MatchStrategy.EXACT, 1),
    ("pass2_whitespace", MatchStrategy.WHITESPACE, 2),
    ("pass8_ast", MatchStrategy.AST, 8),
    ("pass9_anchor", MatchStrategy.ANCHOR, 9),
]


@pytest.mark.e2e
@pytest.mark.parametrize(("case", "strategy", "pass_number"), DEFAULT_CHAIN_CASES)
def test_default_chain_edits_real_file(
    fixture_text,
    copy_case_file,
    case: str,
    strategy: MatchStrategy,
    pass_number: int,
) -> None:
    target = copy_case_file(case)
    editor = EditFile()
    editor.read_file(target)

    result = editor.edit_file(
        target,
        old_text=fixture_text(case, "old.txt"),
        new_text=fixture_text(case, "replacement.txt"),
    )

    assert result.success, result.error
    assert result.strategy_used == strategy
    assert result.pass_number == pass_number
    assert target.read_text(encoding="utf-8") == fixture_text(case, "expected_after.py")
