"""
Pass 8 – Abstract Syntax Tree (AST) Structural Matching
========================================================
For Python files this pass parses both the file and old_text into ASTs and
attempts to find the node whose *unparsed* source is structurally equivalent
to old_text, ignoring comments, docstrings, and whitespace differences.

Support for additional languages (Rust, C++) is possible via ``ast-grep``
(``pip install "edit-file[full]"``), which is loaded lazily.  The pass
gracefully returns None for unsupported file types or if parsing fails.
"""
from __future__ import annotations

import ast
import textwrap
from typing import Optional

from models import MatchResult, MatchStrategy
from passes.base import ReconcilerPass


def _ast_normalize(source: str) -> Optional[str]:
    """Parse source into an AST and unparse it to canonical form."""
    try:
        tree = ast.parse(textwrap.dedent(source))
        return ast.unparse(tree)
    except SyntaxError:
        return None


def _iter_node_sources(content: str) -> list[tuple[str, int, int]]:
    """
    Walk the file's AST and yield (unparsed_source, char_start, char_end)
    for every top-level and nested statement node that carries line info.
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    lines = content.splitlines(keepends=True)
    results: list[tuple[str, int, int]] = []

    for node in ast.walk(tree):
        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
                ast.If,
                ast.For,
                ast.While,
                ast.With,
                ast.Try,
                ast.ExceptHandler,
                ast.Match,
            ),
        ):
            continue
        if not hasattr(node, "lineno") or not hasattr(node, "end_lineno"):
            continue

        line_start = node.lineno - 1
        line_end = (node.end_lineno or node.lineno)

        try:
            node_src = "".join(lines[line_start:line_end])
            unparsed = _ast_normalize(node_src)
            if unparsed is None:
                continue
            char_start = sum(len(l) for l in lines[:line_start])
            char_end = sum(len(l) for l in lines[:line_end])
            results.append((unparsed, char_start, char_end))
        except Exception:
            continue

    return results


class ASTStructuralPass(ReconcilerPass):
    label = "AST Structural Traversal"
    strategy = MatchStrategy.AST
    pass_number = 8

    def find(self, content: str, old_text: str) -> Optional[MatchResult]:
        query_norm = _ast_normalize(old_text)
        if query_norm is None:
            return None  # old_text isn't valid Python; skip.

        candidates = _iter_node_sources(content)
        if not candidates:
            return None

        matches: list[tuple[int, int]] = []
        for node_norm, char_start, char_end in candidates:
            if node_norm == query_norm:
                matches.append((char_start, char_end))

        if not matches:
            return None
        if len(matches) > 1:
            # Multiple structurally identical blocks; can't disambiguate.
            return None

        char_start, char_end = matches[0]
        return self._make_result(content, char_start, char_end, confidence=0.93)