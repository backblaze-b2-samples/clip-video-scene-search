"""Video entity metadata store on B2.

Owns the app's prefix scheme and the meta.json read/write/list logic. No boto3
here — all object I/O goes through ``repo/store``. Heavy segmentation and
embedding live in ``service/ingest``; search lives in ``service/search``.
"""

from __future__ import annotations

import re
import uuid

from app.repo import store
from app.types import Scene, Video, VideoDetail

# --- Prefix scheme (single bucket; every delete is prefix-scoped) ---
VIDEOS_PREFIX = "videos/"
SCENES_CLIPS_PREFIX = "scenes/clips/"
SCENES_KEYFRAMES_PREFIX = "scenes/keyframes/"
SCENES_EMBED_PREFIX = "scenes/embed/"
INDEX_KEY = "scenes/index/index.faiss"
MAPPING_KEY = "scenes/index/mapping.json"

_VIDEO_ID_RE = re.compile(r"^[a-z0-9]{8,32}$")


class VideoNotFound(Exception):
    def __init__(self, video_id: str):
        self.video_id = video_id
        super().__init__(f"Video not found: {video_id}")


class InvalidVideoId(Exception):
    def __init__(self, video_id: str):
        self.video_id = video_id
        super().__init__(f"Invalid video id: {video_id}")


def new_video_id() -> str:
    return uuid.uuid4().hex[:12]


def validate_video_id(video_id: str) -> None:
    """Reject any id that isn't a plain slug — the only thing ever interpolated
    into a delete_prefix, so this is a path-traversal guard, not cosmetic."""
    if not _VIDEO_ID_RE.match(video_id or ""):
        raise InvalidVideoId(video_id)


# --- Key builders ---
def meta_key(video_id: str) -> str:
    return f"{VIDEOS_PREFIX}{video_id}/meta.json"


def source_key(video_id: str, ext: str) -> str:
    ext = ext.lstrip(".") or "mp4"
    return f"{VIDEOS_PREFIX}{video_id}/source.{ext}"


def clip_key(video_id: str, scene_number: int) -> str:
    return f"{SCENES_CLIPS_PREFIX}{video_id}/{scene_number}.mp4"


def keyframe_key(video_id: str, scene_number: int) -> str:
    return f"{SCENES_KEYFRAMES_PREFIX}{video_id}/{scene_number}.jpg"


def embed_key(video_id: str, scene_number: int) -> str:
    return f"{SCENES_EMBED_PREFIX}{video_id}/{scene_number}.npy"


def video_prefixes(video_id: str) -> list[str]:
    """Every prefix that a delete must sweep for one video."""
    return [
        f"{VIDEOS_PREFIX}{video_id}/",
        f"{SCENES_CLIPS_PREFIX}{video_id}/",
        f"{SCENES_KEYFRAMES_PREFIX}{video_id}/",
        f"{SCENES_EMBED_PREFIX}{video_id}/",
    ]


# --- Meta persistence ---
def save_meta(meta: dict) -> None:
    store.write_json(meta_key(meta["id"]), meta)


def load_meta(video_id: str) -> dict:
    validate_video_id(video_id)
    if not store.object_exists(meta_key(video_id)):
        raise VideoNotFound(video_id)
    return store.read_json(meta_key(video_id))


def list_videos() -> list[Video]:
    """Every video in the library, newest-first by creation time."""
    videos: list[Video] = []
    for item in store.list_prefix(VIDEOS_PREFIX):
        if not item["key"].endswith("/meta.json"):
            continue
        try:
            meta = store.read_json(item["key"])
            videos.append(to_video(meta))
        except (RuntimeError, KeyError):
            # A half-written or foreign meta.json shouldn't sink the whole list.
            continue
    videos.sort(key=lambda v: v.created_at, reverse=True)
    return videos


# --- Model conversion ---
def to_video(meta: dict) -> Video:
    scenes = meta.get("scenes", [])
    return Video(
        id=meta["id"],
        title=meta["title"],
        status=meta["status"],
        source_key=meta["source_key"],
        source_filename=meta.get("source_filename", ""),
        scene_count=len(scenes),
        embedded_count=sum(1 for s in scenes if s.get("embedded")),
        duration_seconds=meta.get("duration_seconds"),
        scene_threshold=meta.get("scene_threshold", 0.0),
        clip_model=meta.get("clip_model", ""),
        error=meta.get("error"),
        created_at=meta["created_at"],
        updated_at=meta["updated_at"],
    )


def to_video_detail(meta: dict, *, presign: bool = True) -> VideoDetail:
    base = to_video(meta)
    scenes: list[Scene] = []
    for s in meta.get("scenes", []):
        scene = Scene(
            number=s["number"],
            start_seconds=s["start_seconds"],
            end_seconds=s["end_seconds"],
            start_timecode=s["start_timecode"],
            end_timecode=s["end_timecode"],
            keyframe_key=s["keyframe_key"],
            clip_key=s["clip_key"],
            embedded=s.get("embedded", False),
        )
        if presign:
            scene.keyframe_url = store.presign_get(scene.keyframe_key)
            scene.clip_url = store.presign_get(scene.clip_key)
        scenes.append(scene)
    return VideoDetail(**base.model_dump(), scenes=scenes)
