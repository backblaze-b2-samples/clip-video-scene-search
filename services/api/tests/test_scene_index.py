"""FAISS scene-index unit tests (no model download).

Skipped when the native ML deps aren't installed (e.g. a lean local venv);
CI installs the full lock, so it runs there. Exercises index build, cosine
ranking, and the .npy round-trip used to persist keyframe vectors on B2.
"""

import pytest

pytest.importorskip("faiss")
pytest.importorskip("numpy")

import numpy as np

from app.repo import faiss_index


def _unit(vec) -> np.ndarray:
    arr = np.asarray(vec, dtype="float32")
    return arr / np.linalg.norm(arr)


def test_npy_roundtrip():
    vec = _unit([0.1, 0.2, 0.3, 0.4])
    restored = faiss_index.from_npy_bytes(faiss_index.to_npy_bytes(vec))
    assert restored.dtype == np.float32
    np.testing.assert_allclose(restored, vec, rtol=1e-6)


def test_build_and_search_ranks_nearest_first():
    vectors = [
        _unit([1.0, 0.0, 0.0]),  # row 0
        _unit([0.0, 1.0, 0.0]),  # row 1
        _unit([0.0, 0.0, 1.0]),  # row 2
    ]
    index_bytes = faiss_index.build_index(vectors)

    query = _unit([0.9, 0.1, 0.0])  # closest to row 0
    results = faiss_index.search_index(index_bytes, query, top_k=3)

    assert results, "expected non-empty results"
    assert results[0][0] == 0  # best row is the aligned vector
    # Scores are descending cosine similarities in [-1, 1].
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == pytest.approx(1.0, abs=0.2)


def test_search_top_k_clamped_to_corpus():
    vectors = [_unit([1.0, 0.0]), _unit([0.0, 1.0])]
    index_bytes = faiss_index.build_index(vectors)
    results = faiss_index.search_index(index_bytes, _unit([1.0, 0.0]), top_k=10)
    assert len(results) == 2


def test_build_index_rejects_empty():
    with pytest.raises(ValueError):
        faiss_index.build_index([])
