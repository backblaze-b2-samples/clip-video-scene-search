import logging

from fastapi import APIRouter, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.config import settings
from app.service import search as search_service
from app.types import SearchResponse, TextSearchRequest

logger = logging.getLogger(__name__)

router = APIRouter()

# CLIP embedding is blocking (and downloads weights on first use), so the text
# handler is a sync `def` — Starlette runs it in the threadpool — and the image
# handler offloads the embed with run_in_threadpool after the async file read.


@router.post("/search/text", response_model=SearchResponse)
def search_text_endpoint(body: TextSearchRequest):
    try:
        return search_service.search_text(body.query, body.top_k)
    except RuntimeError as e:
        logger.warning("Text search failed: %s", e)
        raise HTTPException(status_code=502, detail="Search failed") from None


@router.post("/search/image", response_model=SearchResponse)
async def search_image_endpoint(
    file: UploadFile,
    top_k: int | None = Query(default=None, ge=1, le=100),
):
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > settings.max_file_size:
            raise HTTPException(status_code=413, detail="Image too large")
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise HTTPException(status_code=400, detail="Empty image upload")

    try:
        return await run_in_threadpool(search_service.search_image, data, top_k)
    except RuntimeError as e:
        logger.warning("Image search failed: %s", e)
        raise HTTPException(status_code=502, detail="Search failed") from None
