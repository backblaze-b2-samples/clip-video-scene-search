"""Contract/behaviour tests for the Video lifecycle routes.

The service and repo layers are monkeypatched, so these run without B2, ffmpeg,
or the CLIP/FAISS native stack — they exercise routing, status codes, and the
request/response contract only.
"""

import pytest

from app.service import ingest
from app.service import videos as vids
from app.types import Video

VID = "vid123456789a"  # matches the ^[a-z0-9]{8,32}$ id shape


def _fake_meta(video_id: str = VID, status: str = "segmented") -> dict:
    now = "2026-08-03T00:00:00+00:00"
    return {
        "id": video_id,
        "title": "My Clip",
        "status": status,
        "source_key": f"videos/{video_id}/source.mp4",
        "source_filename": "clip.mp4",
        "duration_seconds": 12.0,
        "scene_threshold": 27.0,
        "clip_model": "ViT-B-32/laion2b_s34b_b79k",
        "created_at": now,
        "updated_at": now,
        "scenes": [
            {
                "number": 1,
                "start_seconds": 0.0,
                "end_seconds": 3.0,
                "start_timecode": "00:00:00.000",
                "end_timecode": "00:00:03.000",
                "keyframe_key": f"scenes/keyframes/{video_id}/1.jpg",
                "clip_key": f"scenes/clips/{video_id}/1.mp4",
                "embedded": False,
            }
        ],
    }


def _fake_video(status: str = "segmented") -> Video:
    return vids.to_video(_fake_meta(status=status))


@pytest.mark.asyncio
async def test_list_videos_empty(client, monkeypatch):
    monkeypatch.setattr(vids, "list_videos", lambda: [])
    response = await client.get("/videos")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_video_detail(client, monkeypatch):
    monkeypatch.setattr(vids, "load_meta", lambda vid: _fake_meta())
    monkeypatch.setattr(
        "app.repo.store.presign_get", lambda key, expires_in=3600: f"https://signed/{key}"
    )
    response = await client.get(f"/videos/{VID}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == VID
    assert body["scene_count"] == 1
    assert body["scenes"][0]["keyframe_url"].startswith("https://signed/")


@pytest.mark.asyncio
async def test_get_video_invalid_id(client):
    response = await client.get("/videos/../etc")
    # Path traversal never reaches the handler with a valid slug; a 404 (no
    # route match) or 400 (invalid id) are both correct rejections.
    assert response.status_code in (400, 404)


@pytest.mark.asyncio
async def test_get_video_not_found(client, monkeypatch):
    def _raise(vid):
        raise vids.VideoNotFound(vid)

    monkeypatch.setattr(vids, "load_meta", _raise)
    response = await client.get(f"/videos/{VID}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_video(client, monkeypatch):
    captured = {}

    def _fake_create(**kwargs):
        captured.update(kwargs)
        return _fake_video()

    monkeypatch.setattr(ingest, "create_video", _fake_create)
    response = await client.post(
        "/videos",
        files={"file": ("clip.mp4", b"\x00\x00\x00\x18ftypmp42", "video/mp4")},
        data={"title": "My Clip", "scene_threshold": "35"},
    )
    assert response.status_code == 200
    assert captured["title"] == "My Clip"
    assert captured["scene_threshold"] == 35.0


@pytest.mark.asyncio
async def test_rename_video(client, monkeypatch):
    monkeypatch.setattr(vids, "load_meta", lambda vid: _fake_meta())

    def _fake_rename(vid, title):
        meta = _fake_meta()
        meta["title"] = title
        return vids.to_video(meta)

    monkeypatch.setattr(ingest, "rename_video", _fake_rename)
    response = await client.patch(f"/videos/{VID}", json={"title": "Renamed"})
    assert response.status_code == 200
    assert response.json()["title"] == "Renamed"


@pytest.mark.asyncio
async def test_delete_video(client, monkeypatch):
    monkeypatch.setattr(vids, "load_meta", lambda vid: _fake_meta())
    monkeypatch.setattr(ingest, "delete_video", lambda vid: None)
    response = await client.delete(f"/videos/{VID}")
    assert response.status_code == 200
    assert response.json() == {"deleted": True, "id": VID}


@pytest.mark.asyncio
async def test_build_index_returns_indexing(client, monkeypatch):
    monkeypatch.setattr(vids, "load_meta", lambda vid: _fake_meta())
    monkeypatch.setattr(vids, "save_meta", lambda meta: None)
    # Background embedding must not run for real in the test.
    monkeypatch.setattr(ingest, "run_index_background", lambda vid: None)
    response = await client.post(f"/videos/{VID}/index")
    assert response.status_code == 200
    assert response.json()["status"] == "indexing"


@pytest.mark.asyncio
async def test_library_summary(client, monkeypatch):
    from app.service import library
    from app.types import LibrarySummary

    def _fake_summary():
        return LibrarySummary(
            total_videos=1,
            segmented_videos=1,
            indexed_videos=0,
            total_scenes=1,
            embedded_scenes=0,
            source_bytes=100,
            scene_asset_bytes=200,
            total_bytes=300,
            total_bytes_human="300 B",
            index_present=False,
        )

    monkeypatch.setattr(library, "summarize", _fake_summary)
    response = await client.get("/library/summary")
    assert response.status_code == 200
    assert response.json()["total_videos"] == 1
