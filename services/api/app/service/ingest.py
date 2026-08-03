"""Ingest pipeline: segment on create, embed + index on run.

Split to mirror the cheap-on-create / heavy-on-run pattern:
- ``create_video`` uploads the source, runs PySceneDetect, cuts a clip and
  extracts a keyframe per scene, and writes meta.json with status ``segmented``.
  It does NOT touch CLIP — the multi-GB model download is deferred.
- ``run_index`` embeds every keyframe with CLIP, stores per-keyframe ``.npy``
  vectors, and rebuilds the global FAISS scene index (status ``indexed``).
  Per-scene progress is persisted so a polling UI advances determinately.

boto3 never appears here; object I/O goes through ``repo/store`` and the ML
work through the lazy ``repo/clip`` + ``repo/faiss_index`` adapters.
"""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import UTC, datetime

from app.config import settings
from app.repo import clip, faiss_index, scene_detect, store, video_ffmpeg
from app.service import videos as vids
from app.types import Video

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _content_type_for(ext: str) -> str:
    return {
        "mp4": "video/mp4",
        "mov": "video/quicktime",
        "webm": "video/webm",
        "mkv": "video/x-matroska",
        "avi": "video/x-msvideo",
    }.get(ext.lower(), "video/mp4")


def create_video(
    *,
    file_bytes: bytes,
    filename: str,
    title: str,
    scene_threshold: float | None = None,
    video_id: str | None = None,
) -> Video:
    """Upload + segment a source video into scene clips and keyframes.

    Returns the ``segmented`` Video. Idempotent-friendly: pass ``video_id`` to
    control the id (the seed script does this to stay idempotent).

    The CLIP model is a single GLOBAL/deploy setting (``settings.clip_model``),
    not a per-video choice: every keyframe vector must share one dimensionality
    so they can live in the one shared FAISS index. We record it on the video as
    read-only provenance (the model this index is/was built with).
    """
    video_id = video_id or vids.new_video_id()
    vids.validate_video_id(video_id)
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "mp4").lower()
    threshold = settings.scene_threshold if scene_threshold is None else scene_threshold
    model = settings.clip_model

    src_key = vids.source_key(video_id, ext)
    store.put_bytes(src_key, file_bytes, content_type=_content_type_for(ext))

    scenes_meta: list[dict] = []
    duration: float | None = None
    with tempfile.TemporaryDirectory(prefix="cvss-") as tmp:
        local_src = os.path.join(tmp, f"source.{ext}")
        with open(local_src, "wb") as fh:
            fh.write(file_bytes)

        detected = scene_detect.detect_scenes(
            local_src,
            threshold=threshold,
            min_scene_len_seconds=settings.min_scene_len_seconds,
        )
        if detected:
            duration = detected[-1].end_seconds

        for scene in detected:
            clip_path = os.path.join(tmp, f"{scene.number}.mp4")
            frame_path = os.path.join(tmp, f"{scene.number}.jpg")
            video_ffmpeg.cut_clip(
                local_src, scene.start_seconds, scene.end_seconds, clip_path
            )
            video_ffmpeg.extract_keyframe(
                local_src, scene.midpoint_seconds, frame_path
            )
            ck = vids.clip_key(video_id, scene.number)
            kk = vids.keyframe_key(video_id, scene.number)
            with open(clip_path, "rb") as fh:
                store.put_bytes(ck, fh.read(), content_type="video/mp4")
            with open(frame_path, "rb") as fh:
                store.put_bytes(kk, fh.read(), content_type="image/jpeg")
            scenes_meta.append(
                {
                    "number": scene.number,
                    "start_seconds": scene.start_seconds,
                    "end_seconds": scene.end_seconds,
                    "start_timecode": scene.start_timecode,
                    "end_timecode": scene.end_timecode,
                    "keyframe_key": kk,
                    "clip_key": ck,
                    "embedded": False,
                }
            )

    now = _now()
    meta = {
        "id": video_id,
        "title": title or filename or video_id,
        "status": "segmented",
        "source_key": src_key,
        "source_filename": filename,
        "duration_seconds": duration,
        "scene_threshold": threshold,
        "clip_model": model,
        "created_at": now,
        "updated_at": now,
        "scenes": scenes_meta,
    }
    vids.save_meta(meta)
    logger.info(
        "Segmented video id=%s scenes=%d threshold=%.1f",
        video_id,
        len(scenes_meta),
        threshold,
    )
    return vids.to_video(meta)


def run_index(video_id: str) -> Video:
    """Embed every keyframe with CLIP and (re)build the global scene index."""
    meta = vids.load_meta(video_id)
    meta["status"] = "indexing"
    # Always the global index model — embedding uses settings.clip_model, so the
    # recorded provenance must match it (never a stale per-video value).
    meta["clip_model"] = settings.clip_model
    meta["updated_at"] = _now()
    vids.save_meta(meta)

    for scene in meta["scenes"]:
        frame_bytes = store.get_bytes(scene["keyframe_key"])
        vector = clip.embed_image(frame_bytes)
        store.put_bytes(
            vids.embed_key(video_id, scene["number"]),
            faiss_index.to_npy_bytes(vector),
            content_type="application/octet-stream",
        )
        scene["embedded"] = True
        # Persist progress per scene so the polling UI advances determinately.
        meta["updated_at"] = _now()
        vids.save_meta(meta)

    rebuild_index()

    meta["status"] = "indexed"
    meta["updated_at"] = _now()
    vids.save_meta(meta)
    logger.info("Indexed video id=%s scenes=%d", video_id, len(meta["scenes"]))
    return vids.to_video(meta)


def run_index_background(video_id: str) -> None:
    """Background-task wrapper: run indexing, recording failure on the video so
    the polling UI leaves ``indexing`` for a terminal ``failed`` state instead
    of spinning forever if e.g. the model download fails."""
    try:
        run_index(video_id)
    except Exception as exc:
        logger.exception("Indexing failed for video id=%s", video_id)
        try:
            meta = vids.load_meta(video_id)
            meta["status"] = "failed"
            meta["error"] = str(exc)[:500]
            meta["updated_at"] = _now()
            vids.save_meta(meta)
        except Exception:
            logger.exception("Could not record failure for video id=%s", video_id)


def rebuild_index() -> int:
    """Rebuild the global FAISS index + mapping from every embedded scene.

    Reads persisted ``.npy`` vectors (not in-memory state) so it is correct
    after a delete as well as after a run. Returns the number of indexed scenes.
    An empty corpus clears the index/mapping instead of erroring.
    """
    vectors = []
    mapping: list[dict] = []
    for video in vids.list_videos():
        meta = vids.load_meta(video.id)
        for scene in meta["scenes"]:
            if not scene.get("embedded"):
                continue
            embed_k = vids.embed_key(video.id, scene["number"])
            if not store.object_exists(embed_k):
                continue
            vectors.append(faiss_index.from_npy_bytes(store.get_bytes(embed_k)))
            mapping.append(
                {
                    "video_id": video.id,
                    "video_title": meta["title"],
                    "scene_number": scene["number"],
                    "start_seconds": scene["start_seconds"],
                    "end_seconds": scene["end_seconds"],
                    "start_timecode": scene["start_timecode"],
                    "end_timecode": scene["end_timecode"],
                    "keyframe_key": scene["keyframe_key"],
                    "clip_key": scene["clip_key"],
                }
            )

    if not vectors:
        # Nothing indexed anymore — drop the index so search returns empty.
        for key in (vids.INDEX_KEY, vids.MAPPING_KEY):
            if store.object_exists(key):
                store.delete_prefix(key)
        return 0

    index_bytes = faiss_index.build_index(vectors)
    store.put_bytes(vids.INDEX_KEY, index_bytes, content_type="application/octet-stream")
    store.write_json(vids.MAPPING_KEY, {"scenes": mapping})
    return len(vectors)


def rename_video(video_id: str, title: str) -> Video:
    """Rename a video's title and refresh its title in the search mapping."""
    meta = vids.load_meta(video_id)
    meta["title"] = title
    meta["updated_at"] = _now()
    vids.save_meta(meta)
    _update_mapping_title(video_id, title)
    return vids.to_video(meta)


def delete_video(video_id: str) -> None:
    """Delete a video and every scene/clip/keyframe/embedding, then reindex."""
    vids.load_meta(video_id)  # raises VideoNotFound / InvalidVideoId
    for prefix in vids.video_prefixes(video_id):
        store.delete_prefix(prefix)
    rebuild_index()
    logger.info("Deleted video id=%s", video_id)


def _update_mapping_title(video_id: str, title: str) -> None:
    """Patch a renamed video's title in mapping.json (no FAISS rebuild needed)."""
    if not store.object_exists(vids.MAPPING_KEY):
        return
    mapping = store.read_json(vids.MAPPING_KEY)
    changed = False
    for entry in mapping.get("scenes", []):
        if entry.get("video_id") == video_id and entry.get("video_title") != title:
            entry["video_title"] = title
            changed = True
    if changed:
        store.write_json(vids.MAPPING_KEY, mapping)
