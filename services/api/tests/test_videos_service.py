"""Unit tests for the video meta store: id validation, key builders, and the
prefix-scoped delete guard. No B2, ffmpeg, or ML stack involved."""

import pytest

from app.repo import store
from app.service import videos as vids


def test_validate_video_id_accepts_slug():
    vids.validate_video_id("abc123def456")  # no raise


@pytest.mark.parametrize(
    "bad",
    ["", "../etc", "a/b", "UPPER1234", "has space", "x" * 40, "sh"],
)
def test_validate_video_id_rejects_bad(bad):
    with pytest.raises(vids.InvalidVideoId):
        vids.validate_video_id(bad)


def test_key_builders_are_prefix_scoped():
    vid = "abc123def456"
    assert vids.meta_key(vid) == f"videos/{vid}/meta.json"
    assert vids.source_key(vid, "mov") == f"videos/{vid}/source.mov"
    assert vids.clip_key(vid, 3) == f"scenes/clips/{vid}/3.mp4"
    assert vids.keyframe_key(vid, 3) == f"scenes/keyframes/{vid}/3.jpg"
    assert vids.embed_key(vid, 3) == f"scenes/embed/{vid}/3.npy"
    prefixes = vids.video_prefixes(vid)
    assert all(vid in p and p.endswith("/") for p in prefixes)


def test_delete_prefix_refuses_empty():
    # SAFETY: an empty prefix must never be accepted (would target the bucket).
    with pytest.raises(ValueError):
        store.delete_prefix("")
    with pytest.raises(ValueError):
        store.delete_prefix("   ")
