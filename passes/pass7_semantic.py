"""
Pass 7 – Semantic Duplicate Detection and Vector Embeddings
============================================================
Converts old_text into a dense vector using a lightweight sentence
embedding model (SBERT) and compares it against chunked embeddings of the
target file via cosine similarity.

This pass is *optional*: it activates only if ``sentence-transformers`` and
``numpy`` are installed (``pip install "edit-file[semantic]"``).  When the
dependencies are absent the pass transparently returns None.
"""
from __future__ import annotations

from typing import Optional

from models import MatchResult, MatchStrategy
from passes.base import ReconcilerPass

_THRESHOLD = 0.82
_MODEL_NAME = "all-MiniLM-L6-v2"

# Lazy globals – populated on first use.
_model = None
_np = None


def _load() -> bool:
    """Return True if dependencies could be loaded."""
    global _model, _np
    if _model is not None:
        return True
    try:
        import numpy as np  # noqa: PLC0415
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

        _np = np
        _model = SentenceTransformer(_MODEL_NAME)
        return True
    except ImportError:
        return False


def _cosine(a, b) -> float:  # noqa: ANN001
    norm_a = _np.linalg.norm(a)
    norm_b = _np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(_np.dot(a, b) / (norm_a * norm_b))


class SemanticEmbeddingPass(ReconcilerPass):
    label = "Semantic Vector Embedding"
    strategy = MatchStrategy.SEMANTIC
    pass_number = 7
    threshold: float = _THRESHOLD

    # Number of lines per file chunk to embed.
    chunk_lines: int = 20

    def find(self, content: str, old_text: str) -> Optional[MatchResult]:
        if not _load():
            return None  # Dependencies not installed; skip silently.

        query = old_text.strip()
        if not query:
            return None

        try:
            return self._semantic_find(content, query)
        except Exception:
            return None

    def _semantic_find(self, content: str, query: str) -> Optional[MatchResult]:
        file_lines = content.splitlines(keepends=True)
        n_query_lines = len(query.splitlines())

        # Build overlapping chunks of `n_query_lines` lines.
        chunks: list[tuple[str, int, int]] = []  # (text, line_start, line_end)
        step = max(1, n_query_lines // 2)
        for i in range(0, len(file_lines), step):
            chunk_lines = file_lines[i : i + n_query_lines]
            if not chunk_lines:
                break
            chunks.append(("".join(chunk_lines), i, i + len(chunk_lines)))

        if not chunks:
            return None

        chunk_texts = [c[0] for c in chunks]
        query_vec = _model.encode([query])[0]
        chunk_vecs = _model.encode(chunk_texts)

        best_score = 0.0
        best_chunk: Optional[tuple[str, int, int]] = None

        for chunk, vec in zip(chunks, chunk_vecs):
            score = _cosine(query_vec, vec)
            if score > best_score:
                best_score = score
                best_chunk = chunk

        if best_score < self.threshold or best_chunk is None:
            return None

        _, line_start, line_end = best_chunk
        char_start = sum(len(l) for l in file_lines[:line_start])
        char_end = sum(len(l) for l in file_lines[:line_end])
        return self._make_result(content, char_start, char_end, confidence=best_score)