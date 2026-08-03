"""PySceneDetect wrapper.

`scenedetect` (and the OpenCV backend it uses) is imported lazily inside the
function so importing the app — and running the structural/contract tests —
never pulls the native OpenCV stack.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DetectedScene:
    number: int  # 1-based scene index
    start_seconds: float
    end_seconds: float
    start_timecode: str  # HH:MM:SS.mmm
    end_timecode: str

    @property
    def midpoint_seconds(self) -> float:
        return (self.start_seconds + self.end_seconds) / 2.0


def detect_scenes(
    video_path: str,
    threshold: float,
    min_scene_len_seconds: float = 0.0,
) -> list[DetectedScene]:
    """Split a local video file into scenes with `ContentDetector`.

    Returns a list of `DetectedScene` (1-based, ordered). If the detector finds
    no cuts (e.g. a single continuous shot) the whole video is returned as one
    scene, so every ingested video always yields at least one keyframe.
    """
    from scenedetect import ContentDetector, SceneManager, open_video

    video = open_video(video_path)
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=threshold))
    manager.detect_scenes(video, show_progress=False)
    scene_list = manager.get_scene_list()

    if not scene_list:
        duration = video.duration.get_seconds() if video.duration else 0.0
        return [
            DetectedScene(
                number=1,
                start_seconds=0.0,
                end_seconds=duration,
                start_timecode="00:00:00.000",
                end_timecode=_format_timecode(duration),
            )
        ]

    scenes: list[DetectedScene] = []
    number = 0
    for start, end in scene_list:
        start_s = start.get_seconds()
        end_s = end.get_seconds()
        if (end_s - start_s) < min_scene_len_seconds:
            continue
        number += 1
        scenes.append(
            DetectedScene(
                number=number,
                start_seconds=start_s,
                end_seconds=end_s,
                start_timecode=start.get_timecode(),
                end_timecode=end.get_timecode(),
            )
        )
    # Every scene fell under min length — keep the single longest so ingest is
    # never left with an empty scene list.
    if not scenes:
        start, end = scene_list[0]
        scenes.append(
            DetectedScene(
                number=1,
                start_seconds=start.get_seconds(),
                end_seconds=end.get_seconds(),
                start_timecode=start.get_timecode(),
                end_timecode=end.get_timecode(),
            )
        )
    return scenes


def _format_timecode(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
