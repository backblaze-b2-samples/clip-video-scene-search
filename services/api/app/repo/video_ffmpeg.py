"""Thin wrapper over the BUNDLED ffmpeg binary.

The binary is resolved via ``imageio_ffmpeg.get_ffmpeg_exe()`` and its absolute
path is passed explicitly to every subprocess — the code never assumes a
system/Homebrew ffmpeg is on PATH (Homebrew's is often a slim build). The
import is lazy so app import / structural tests don't require imageio-ffmpeg.
"""

from __future__ import annotations

import subprocess


def ffmpeg_exe() -> str:
    """Absolute path to the bundled ffmpeg binary."""
    from imageio_ffmpeg import get_ffmpeg_exe

    return get_ffmpeg_exe()


def run_ffmpeg(args: list[str]) -> None:
    """Run the bundled ffmpeg with ``args`` (excluding the binary itself).

    Raises RuntimeError on a non-zero exit, surfacing ffmpeg's stderr tail.
    """
    cmd = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip()[-800:]
        raise RuntimeError(f"ffmpeg failed ({proc.returncode}): {tail}")


def cut_clip(src: str, start_seconds: float, end_seconds: float, out_mp4: str) -> None:
    """Cut ``[start, end]`` from ``src`` into a standalone H.264 mp4.

    Re-encodes (rather than stream-copy) so the clip is seekable from its first
    frame regardless of where the source keyframes fall.
    """
    duration = max(0.05, end_seconds - start_seconds)
    run_ffmpeg(
        [
            "-ss", f"{start_seconds:.3f}",
            "-i", src,
            "-t", f"{duration:.3f}",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-an",  # scene clips are visual; drop audio to keep them small
            "-movflags", "+faststart",
            out_mp4,
        ]
    )


def extract_keyframe(src: str, at_seconds: float, out_jpg: str) -> None:
    """Extract a single representative frame at ``at_seconds`` as a JPEG."""
    run_ffmpeg(
        [
            "-ss", f"{at_seconds:.3f}",
            "-i", src,
            "-frames:v", "1",
            "-q:v", "2",
            out_jpg,
        ]
    )
