from pydantic import BaseModel, Field


class SearchHit(BaseModel):
    video_id: str
    video_title: str
    scene_number: int
    start_seconds: float
    end_seconds: float
    start_timecode: str
    end_timecode: str
    score: float
    keyframe_url: str | None = None
    clip_url: str | None = None


class SearchResponse(BaseModel):
    mode: str  # "text" | "image"
    query: str | None = None  # the text query, or None for image search
    top_k: int
    hits: list[SearchHit] = Field(default_factory=list)


class TextSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int | None = Field(default=None, ge=1, le=100)
