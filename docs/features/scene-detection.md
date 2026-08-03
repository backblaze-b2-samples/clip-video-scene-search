<!-- last_verified: 2026-08-03 -->
# Feature: Scene Detection

## Purpose
Split a source video into scenes so each can be clipped, keyframed, and embedded independently.

## Used By
- API: `POST /videos` (during ingest, before clip/keyframe extraction)
- Job: none (runs inline on create, in Starlette's threadpool)

## Core Functions
- `services/api/app/repo/scene_detect.py` — `detect_scenes()`, `DetectedScene`
- `services/api/app/service/ingest.py` — `create_video()` calls the detector

## Canonical Files
- Detector wrapper: `services/api/app/repo/scene_detect.py`

## Inputs
- video_path: str (a local temp copy of the uploaded source)
- threshold: float (PySceneDetect `ContentDetector` threshold; 20 / 27 / 35 from the UI)
- min_scene_len_seconds: float (from settings; discards micro-cuts)

## Outputs
- list[DetectedScene]: 1-based number, start/end seconds, start/end timecode
- No B2 side effect in this module (the caller cuts clips and writes meta)

## Flow
- `open_video()` + `SceneManager` + `ContentDetector(threshold=...)` -> `get_scene_list()`
- Scenes shorter than `min_scene_len_seconds` are dropped
- If the detector finds no cuts (single continuous shot), the whole video is returned as one scene, so ingest always yields at least one keyframe

## Edge Cases
- No cuts detected -> one scene spanning the whole video
- Every scene under the min length -> the single longest scene is kept
- Unreadable video -> the underlying OpenCV/scenedetect error propagates as a 502 from the ingest route

## UX States
- Surfaced only as the scene count on the video after ingest

## Verification
- Test files: `services/api/tests/test_videos.py` (ingest route contract), scene logic exercised via `create_video`
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: `pnpm verify` green; a segmented video reports its scene count

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Scene Clips & Keyframes](scene-clips-keyframes.md)
- [App Workflows](../app-workflows.md)
