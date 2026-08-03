"""Search route + empty-corpus behaviour tests (no CLIP/FAISS needed)."""

import pytest

from app.service import search as search_service
from app.types import SearchHit, SearchResponse


@pytest.mark.asyncio
async def test_search_text_empty_corpus(client, monkeypatch):
    # No index present -> empty hits, not an error (and CLIP is never touched).
    monkeypatch.setattr("app.repo.store.object_exists", lambda key: False)
    response = await client.post("/search/text", json={"query": "a person on a beach"})
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "text"
    assert body["hits"] == []


@pytest.mark.asyncio
async def test_search_text_returns_hits(client, monkeypatch):
    def _fake_search(query, top_k=None):
        return SearchResponse(
            mode="text",
            query=query,
            top_k=top_k or 12,
            hits=[
                SearchHit(
                    video_id="vid123456789a",
                    video_title="My Clip",
                    scene_number=2,
                    start_seconds=3.0,
                    end_seconds=6.0,
                    start_timecode="00:00:03.000",
                    end_timecode="00:00:06.000",
                    score=0.87,
                    keyframe_url="https://signed/keyframe.jpg",
                    clip_url="https://signed/clip.mp4",
                )
            ],
        )

    monkeypatch.setattr(search_service, "search_text", _fake_search)
    response = await client.post(
        "/search/text", json={"query": "sunset", "top_k": 5}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["top_k"] == 5
    assert body["hits"][0]["scene_number"] == 2
    assert body["hits"][0]["score"] == pytest.approx(0.87)


@pytest.mark.asyncio
async def test_search_text_rejects_empty_query(client):
    response = await client.post("/search/text", json={"query": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_image_empty_corpus(client, monkeypatch):
    monkeypatch.setattr("app.repo.store.object_exists", lambda key: False)
    response = await client.post(
        "/search/image",
        files={"file": ("still.jpg", b"\xff\xd8\xff\xe0stub", "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "image"
    assert body["hits"] == []


def test_search_text_service_empty_without_clip(monkeypatch):
    """Unit: empty corpus returns before any CLIP import happens."""
    monkeypatch.setattr("app.repo.store.object_exists", lambda key: False)
    result = search_service.search_text("query", top_k=3)
    assert result.hits == []
    assert result.top_k == 3
