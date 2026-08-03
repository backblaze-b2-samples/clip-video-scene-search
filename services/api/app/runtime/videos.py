import logging
from datetime import UTC, datetime

# Sync `def` handlers (except the multipart upload) run in Starlette's
# threadpool, so the blocking B2 / ffmpeg / CLIP work never stalls the event
# loop — same rationale as runtime/files.py.
from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, UploadFile

from app.config import settings
from app.service import ingest, library
from app.service import videos as vids
from app.service.videos import InvalidVideoId, VideoNotFound
from app.types import LibrarySummary, RenameVideoRequest, Video, VideoDetail

logger = logging.getLogger(__name__)

router = APIRouter()

# SECURITY: these routes are intentionally UNAUTHENTICATED and single-tenant
# (see docs/SECURITY.md), matching the file/upload routes. A multi-tenant clone
# must add auth AND scope every prefix to the caller.


def _load_or_404(video_id: str) -> dict:
    try:
        return vids.load_meta(video_id)
    except InvalidVideoId:
        raise HTTPException(status_code=400, detail="Invalid video id") from None
    except VideoNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get("/videos", response_model=list[Video])
def list_videos_endpoint():
    return vids.list_videos()


@router.post("/videos", response_model=Video)
async def create_video_endpoint(
    file: UploadFile,
    title: str = Form(default=""),
    scene_threshold: float | None = Form(default=None),
    clip_model: str | None = Form(default=None),
):
    from fastapi.concurrency import run_in_threadpool

    # Stream with an early size cap (mirrors runtime/upload.py).
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > settings.max_file_size:
            raise HTTPException(status_code=413, detail="Video too large")
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise HTTPException(status_code=400, detail="Empty video upload")

    try:
        return await run_in_threadpool(
            ingest.create_video,
            file_bytes=data,
            filename=file.filename or "video.mp4",
            title=title,
            scene_threshold=scene_threshold,
            clip_model=clip_model,
        )
    except RuntimeError as e:
        logger.warning("Video ingest failed: %s", e)
        raise HTTPException(status_code=502, detail="Failed to segment video") from None


@router.get("/videos/{video_id}", response_model=VideoDetail)
def get_video_endpoint(video_id: str):
    meta = _load_or_404(video_id)
    return vids.to_video_detail(meta)


@router.patch("/videos/{video_id}", response_model=Video)
def rename_video_endpoint(video_id: str, body: RenameVideoRequest):
    _load_or_404(video_id)
    return ingest.rename_video(video_id, body.title)


@router.delete("/videos/{video_id}")
def delete_video_endpoint(video_id: str):
    _load_or_404(video_id)
    ingest.delete_video(video_id)
    logger.info("Video deleted: id=%s", video_id)
    return {"deleted": True, "id": video_id}


@router.post("/videos/{video_id}/index", response_model=Video)
def build_index_endpoint(video_id: str, background: BackgroundTasks):
    """Kick off CLIP embedding + FAISS (re)build in the background.

    Returns immediately with status ``indexing``; the UI polls
    ``GET /videos/{id}`` until it reaches ``indexed`` (or ``failed``).
    """
    meta = _load_or_404(video_id)
    meta["status"] = "indexing"
    meta["error"] = None
    meta["updated_at"] = datetime.now(UTC).isoformat()
    vids.save_meta(meta)
    background.add_task(ingest.run_index_background, video_id)
    return vids.to_video(meta)


@router.get("/library/summary", response_model=LibrarySummary)
def library_summary_endpoint():
    return library.summarize()
