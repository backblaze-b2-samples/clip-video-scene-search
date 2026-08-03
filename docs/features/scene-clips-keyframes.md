<!-- last_verified: 2026-08-03 -->
# Feature: Scene Clips & Keyframes

## Purpose
For each detected scene, produce a standalone clip and one representative keyframe, stored in B2.

## Used By
- API: `POST /videos` (ingest, per scene)

## Core Functions
- `services/api/app/repo/video_ffmpeg.py` — `ffmpeg_exe()`, `run_ffmpeg()`, `cut_clip()`, `extract_keyframe()`
- `services/api/app/service/ingest.py` — `create_video()` orchestrates per-scene extraction and upload

## Canonical Files
- ffmpeg wrapper: `services/api/app/repo/video_ffmpeg.py`

## Inputs
- src: str (local source path)
- start_seconds / end_seconds / at_seconds: float (from the detected scene)
- out path: str (temp file, then uploaded to B2)

## Outputs
- B2 objects: `scenes/clips/<id>/<n>.mp4` (H.264, re-encoded so it is seekable from frame 0) and `scenes/keyframes/<id>/<n>.jpg`

## Flow
- The ffmpeg binary is resolved via `imageio_ffmpeg.get_ffmpeg_exe()` — the BUNDLED binary, never a system/Homebrew ffmpeg (which may be a slim build). Its absolute path is passed to every subprocess.
- Per scene: `cut_clip()` re-encodes `[start, end]` to mp4; `extract_keyframe()` grabs a single JPEG at the scene midpoint
- Each output is uploaded to its B2 prefix; the keys are recorded in meta.json

## Edge Cases
- ffmpeg non-zero exit -> `run_ffmpeg` raises RuntimeError with the stderr tail -> 502 from the ingest route
- Very short scene -> a minimum clip duration floor keeps the cut valid

## UX States
- Rendered on the video detail page and in search results as keyframe thumbnails with an "Open clip" link

## Verification
- Test files: `services/api/tests/test_videos.py`
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: after ingest, each scene has a keyframe and clip key in meta.json

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Scene Detection](scene-detection.md)
- [App Workflows](../app-workflows.md)
