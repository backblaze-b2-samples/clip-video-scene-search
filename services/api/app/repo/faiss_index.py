"""FAISS scene index (cosine similarity over L2-normalized keyframe vectors).

One vector per scene keyframe, so a flat inner-product index (`IndexFlatIP`) is
exact cosine ranking on already-normalized vectors — simpler than a per-patch
MaxSim index. faiss and numpy are imported lazily and faiss is pinned to a
single OpenMP thread (the env-var guard in ``repo/__init__`` is not enough on
its own to avoid the torch+faiss dual-OpenMP abort on macOS arm64).
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

_faiss_lock = threading.Lock()
_threads_pinned = False


def _faiss():
    global _threads_pinned
    import faiss

    with _faiss_lock:
        if not _threads_pinned:
            faiss.omp_set_num_threads(1)
            _threads_pinned = True
    return faiss


def to_npy_bytes(vec: np.ndarray) -> bytes:
    """Serialize a 1-D float32 vector to .npy bytes for B2 storage."""
    import io

    import numpy as np

    buffer = io.BytesIO()
    np.save(buffer, np.asarray(vec, dtype="float32"))
    return buffer.getvalue()


def from_npy_bytes(data: bytes) -> np.ndarray:
    """Load a 1-D float32 vector from .npy bytes."""
    import io

    import numpy as np

    return np.load(io.BytesIO(data)).astype("float32")


def build_index(vectors: list[np.ndarray]) -> bytes:
    """Build an ``IndexFlatIP`` over ``vectors`` and return serialized bytes.

    ``vectors`` must be L2-normalized (they are, from ``repo/clip``). Row order
    is preserved, so the caller's parallel mapping list stays aligned. An empty
    list raises ValueError — callers guard on an empty corpus first.
    """
    import numpy as np

    if not vectors:
        raise ValueError("cannot build an index over zero vectors")
    faiss = _faiss()
    matrix = np.vstack([np.asarray(v, dtype="float32") for v in vectors])
    dim = matrix.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(matrix)
    return faiss.serialize_index(index).tobytes()


def search_index(
    index_bytes: bytes, query: np.ndarray, top_k: int
) -> list[tuple[int, float]]:
    """Return up to ``top_k`` ``(row, score)`` pairs, best first.

    ``row`` indexes into the caller's mapping list. Deserializes the index from
    bytes each call — fine for the demo's index sizes and keeps the repo
    stateless. Returns an empty list for a non-positive ``top_k``.
    """
    import numpy as np

    if top_k <= 0:
        return []
    faiss = _faiss()
    buffer = np.frombuffer(index_bytes, dtype="uint8")
    index = faiss.deserialize_index(buffer)
    query_matrix = np.asarray(query, dtype="float32").reshape(1, -1)
    k = min(top_k, index.ntotal)
    if k == 0:
        return []
    scores, rows = index.search(query_matrix, k)
    return [
        (int(row), float(score))
        for row, score in zip(rows[0], scores[0], strict=False)
        if row >= 0
    ]
