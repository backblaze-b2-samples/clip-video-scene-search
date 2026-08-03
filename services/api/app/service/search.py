"""Text-to-scene and image-to-scene search over the FAISS scene index.

Both paths embed the query with CLIP (same space as the keyframe vectors) and
cosine-rank against the global index stored in B2. An empty corpus (no index
yet) returns empty hits rather than an error.
"""

from __future__ import annotations

from app.config import settings
from app.repo import clip, faiss_index, store
from app.service import videos as vids
from app.types import SearchHit, SearchResponse


def _load_index() -> tuple[bytes | None, list[dict]]:
    if not store.object_exists(vids.INDEX_KEY) or not store.object_exists(
        vids.MAPPING_KEY
    ):
        return None, []
    index_bytes = store.get_bytes(vids.INDEX_KEY)
    mapping = store.read_json(vids.MAPPING_KEY).get("scenes", [])
    return index_bytes, mapping


def _hits_from(index_bytes: bytes, mapping: list[dict], query_vec, top_k: int) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for row, score in faiss_index.search_index(index_bytes, query_vec, top_k):
        if row < 0 or row >= len(mapping):
            continue
        m = mapping[row]
        hits.append(
            SearchHit(
                video_id=m["video_id"],
                video_title=m.get("video_title", m["video_id"]),
                scene_number=m["scene_number"],
                start_seconds=m["start_seconds"],
                end_seconds=m["end_seconds"],
                start_timecode=m["start_timecode"],
                end_timecode=m["end_timecode"],
                score=score,
                keyframe_url=store.presign_get(m["keyframe_key"]),
                clip_url=store.presign_get(m["clip_key"]),
            )
        )
    return hits


def _resolve_top_k(top_k: int | None) -> int:
    return top_k if top_k and top_k > 0 else settings.search_top_k


def search_text(query: str, top_k: int | None = None) -> SearchResponse:
    k = _resolve_top_k(top_k)
    index_bytes, mapping = _load_index()
    if index_bytes is None:
        return SearchResponse(mode="text", query=query, top_k=k, hits=[])
    query_vec = clip.embed_text(query)
    return SearchResponse(
        mode="text", query=query, top_k=k, hits=_hits_from(index_bytes, mapping, query_vec, k)
    )


def search_image(data: bytes, top_k: int | None = None) -> SearchResponse:
    k = _resolve_top_k(top_k)
    index_bytes, mapping = _load_index()
    if index_bytes is None:
        return SearchResponse(mode="image", query=None, top_k=k, hits=[])
    query_vec = clip.embed_image(data)
    return SearchResponse(
        mode="image", query=None, top_k=k, hits=_hits_from(index_bytes, mapping, query_vec, k)
    )
