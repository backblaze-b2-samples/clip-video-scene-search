from datetime import datetime

from pydantic import BaseModel, Field

# Lifecycle status of a video in the library.
#   segmented -> scenes cut + keyframes extracted (no embeddings yet)
#   indexing  -> "Build scene index" running (embedding keyframes)
#   indexed   -> keyframes embedded and present in the FAISS scene index
VideoStatus = str


class Scene(BaseModel):
    number: int  # 1-based scene index within the video
    start_seconds: float
    end_seconds: float
    start_timecode: str
    end_timecode: str
    keyframe_key: str
    clip_key: str
    embedded: bool = False
    # Populated on the detail response so the browser can render/stream directly.
    keyframe_url: str | None = None
    clip_url: str | None = None


class Video(BaseModel):
    id: str
    title: str
    status: VideoStatus
    source_key: str
    source_filename: str
    scene_count: int
    embedded_count: int
    duration_seconds: float | None = None
    scene_threshold: float
    clip_model: str
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class VideoDetail(Video):
    scenes: list[Scene] = Field(default_factory=list)


class RenameVideoRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class LibrarySummary(BaseModel):
    """Sample-scoped footprint over the app's own B2 prefixes (Library view)."""

    total_videos: int
    segmented_videos: int
    indexed_videos: int
    total_scenes: int
    embedded_scenes: int
    source_bytes: int
    scene_asset_bytes: int
    total_bytes: int
    total_bytes_human: str
    index_present: bool
