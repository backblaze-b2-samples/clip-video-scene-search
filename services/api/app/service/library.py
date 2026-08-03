"""Sample-scoped Library view over the app's own B2 prefixes.

Distinct from the generic full-bucket ``/files`` explorer: this reports only the
video-scene corpus the app owns (sources, clips, keyframes, embeddings, index),
so the Library page can show the app's footprint without scanning unrelated
bucket data.
"""

from __future__ import annotations

from app.repo import store
from app.service import videos as vids
from app.types import LibrarySummary
from app.types.formatting import humanize_bytes


def summarize() -> LibrarySummary:
    metas = [vids.load_meta(v.id) for v in vids.list_videos()]

    total_scenes = sum(len(m.get("scenes", [])) for m in metas)
    embedded_scenes = sum(
        1 for m in metas for s in m.get("scenes", []) if s.get("embedded")
    )
    segmented = sum(1 for m in metas if m.get("status") == "segmented")
    indexed = sum(1 for m in metas if m.get("status") == "indexed")

    source_bytes = sum(
        item["size"]
        for item in store.list_prefix(vids.VIDEOS_PREFIX)
        if "/source." in item["key"]
    )
    scene_asset_bytes = 0
    for prefix in (
        vids.SCENES_CLIPS_PREFIX,
        vids.SCENES_KEYFRAMES_PREFIX,
        vids.SCENES_EMBED_PREFIX,
    ):
        scene_asset_bytes += sum(item["size"] for item in store.list_prefix(prefix))

    total_bytes = source_bytes + scene_asset_bytes
    return LibrarySummary(
        total_videos=len(metas),
        segmented_videos=segmented,
        indexed_videos=indexed,
        total_scenes=total_scenes,
        embedded_scenes=embedded_scenes,
        source_bytes=source_bytes,
        scene_asset_bytes=scene_asset_bytes,
        total_bytes=total_bytes,
        total_bytes_human=humanize_bytes(total_bytes),
        index_present=store.object_exists(vids.INDEX_KEY),
    )
