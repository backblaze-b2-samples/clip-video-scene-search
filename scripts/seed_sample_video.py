#!/usr/bin/env python
"""Seed a small, synthetic multi-scene demo video into B2.

Fully offline, deterministic, and idempotent:
- Generates a ~15s clip of five visually distinct 3s segments (different
  lavfi test patterns/colours) with the BUNDLED ffmpeg, so PySceneDetect
  reliably finds hard cuts with no network and no licensing concern (generated
  content is CC0).
- Uploads the source, then segments it (cut per-scene clips + extract
  keyframes) to status ``segmented`` so the Library has rich content on first run.
- Does NOT embed with CLIP — the multi-GB model download is deferred to the
  "Build scene index" action, keeping setup light. Re-running is a no-op once
  the seed video exists.

Realistic-content alternative:
    Instead of the synthetic clip, drop a small CC-BY video (e.g. a short
    Blender open-movie segment) at services/api/.data/seed.mp4 and set
    SEED_SOURCE=services/api/.data/seed.mp4 to ingest that instead. Only use
    footage you have the right to redistribute.

Usage:
    services/api/.venv/bin/python scripts/seed_sample_video.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API_ROOT = REPO_ROOT / "services" / "api"
sys.path.insert(0, str(API_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

from app.config import settings  # noqa: E402
from app.repo import store, video_ffmpeg  # noqa: E402
from app.service import ingest  # noqa: E402
from app.service import videos as vids  # noqa: E402

# Fixed id + title keep the seed idempotent and recognizable in the Library.
SEED_VIDEO_ID = "seedsample01"
SEED_TITLE = "Seed Sample — synthetic multi-scene clip"
SEED_FILENAME = "seed-sample.mp4"

# Five visually distinct 3s lavfi segments -> four hard cuts -> five scenes.
_SEGMENTS = [
    "testsrc=size=320x240:rate=15:duration=3",
    "testsrc2=size=320x240:rate=15:duration=3",
    "smptebars=size=320x240:rate=15:duration=3",
    "rgbtestsrc=size=320x240:rate=15:duration=3",
    "color=c=orange:size=320x240:rate=15:duration=3",
]


def _generate_clip(out_path: str) -> None:
    args: list[str] = []
    for segment in _SEGMENTS:
        args += ["-f", "lavfi", "-i", segment]
    concat_inputs = "".join(f"[{i}:v]" for i in range(len(_SEGMENTS)))
    filtergraph = f"{concat_inputs}concat=n={len(_SEGMENTS)}:v=1:a=0[v]"
    args += [
        "-filter_complex", filtergraph,
        "-map", "[v]",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        out_path,
    ]
    video_ffmpeg.run_ffmpeg(args)


def _preflight() -> None:
    missing = [
        name
        for attr, name in (
            ("b2_application_key_id", "B2_APPLICATION_KEY_ID"),
            ("b2_application_key", "B2_APPLICATION_KEY"),
            ("b2_bucket_name", "B2_BUCKET_NAME"),
            ("b2_region", "B2_REGION"),
        )
        if not getattr(settings, attr)
    ]
    if missing:
        print(
            "Missing B2 configuration: "
            + ", ".join(missing)
            + f".\nAdd them to {REPO_ROOT / '.env'} (see .env.example) and retry.",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> int:
    _preflight()

    if store.object_exists(vids.meta_key(SEED_VIDEO_ID)):
        print(f"Seed video '{SEED_VIDEO_ID}' already exists — nothing to do.")
        return 0

    source_override = os.environ.get("SEED_SOURCE")
    with tempfile.TemporaryDirectory(prefix="cvss-seed-") as tmp:
        if source_override:
            clip_path = source_override
            print(f"Ingesting provided source: {clip_path}")
        else:
            clip_path = os.path.join(tmp, "seed.mp4")
            print("Generating synthetic multi-scene clip with the bundled ffmpeg...")
            _generate_clip(clip_path)

        with open(clip_path, "rb") as fh:
            data = fh.read()

        print("Uploading source and segmenting scenes (no CLIP embedding yet)...")
        video = ingest.create_video(
            file_bytes=data,
            filename=SEED_FILENAME,
            title=SEED_TITLE,
            video_id=SEED_VIDEO_ID,
        )

    print(
        f"Seeded video id={video.id} status={video.status} "
        f"scenes={video.scene_count}.\n"
        "Open the Library, then click \"Build scene index\" to embed keyframes "
        "and enable scene search."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
