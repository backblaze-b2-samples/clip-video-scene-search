<!-- last_verified: 2026-08-03 -->
# Feature: Video Library

## Purpose
Manage the primary entity — a **Video** — across its full lifecycle: create, read, edit (rename), delete, and run (build scene index).

## Used By
- UI: `/library` (list + summary), `/videos/[id]` (detail + actions), `/ingest` (create)
- API: `GET /videos`, `POST /videos`, `GET /videos/{id}`, `PATCH /videos/{id}`, `DELETE /videos/{id}`, `POST /videos/{id}/index`, `GET /library/summary`

## Core Functions
- `services/api/app/service/videos.py` — meta store, prefix scheme, id validation, model conversion
- `services/api/app/service/ingest.py` — `create_video`, `run_index`, `rebuild_index`, `rename_video`, `delete_video`
- `services/api/app/service/library.py` — `summarize()` (sample-scoped footprint)
- `apps/web/src/components/library/library-view.tsx`, `apps/web/src/components/videos/video-detail.tsx`
- `apps/web/src/lib/queries.ts` — `useVideos`, `useVideo` (polls while indexing), `useLibrarySummary`, `useRenameVideo`, `useDeleteVideo`, `useBuildSceneIndex`

## Canonical Files
- Meta store: `services/api/app/service/videos.py`
- Detail UI (all lifecycle verbs): `apps/web/src/components/videos/video-detail.tsx`

## Inputs
- Create: multipart video file + `title` + `scene_threshold` + `clip_model`
- Rename: `{ title }`
- id: a validated slug (`^[a-z0-9]{8,32}$`) — the only thing interpolated into a prefix delete

## Outputs
- `Video` / `VideoDetail` (with scenes, presigned keyframe/clip URLs)
- `LibrarySummary` (videos, scenes, embedded scenes, source/scene bytes, index present)
- Side effects: B2 objects created/removed under the video's prefixes; index rebuilt on run/delete

## Lifecycle (UI completeness — no verb omitted)
- **create** — Ingest page uploads + segments to `segmented`
- **read** — Library list + detail page (scenes as keyframe thumbnails, timecodes, clip links)
- **edit** — Rename dialog, pre-filled with the current title (`PATCH`)
- **delete** — confirm dialog; removes every prefix then rebuilds the index (`DELETE`)
- **run** — "Build scene index": embeds keyframes + rebuilds FAISS, polled to `indexed` (`POST /videos/{id}/index`)

## Form UX conventions
- Ingest (create) form: free-text **Title** with a placeholder hint (defaults to the file name); **Detection threshold** and **CLIP model** are `Select`s (finite sets), with safe-default guidance in `FormDescription` — no autofill button
- Rename (edit) form: single free-text Title, pre-filled with the current value, no default hint (a real resource)

## Library vs Files
- `/library` is sample-scoped (only the app's `videos/` and `scenes/` prefixes). `/files` is the generic full-bucket explorer kept from the starter; `/upload` is the generic raw upload.

## Edge Cases
- Invalid id -> 400; unknown id -> 404
- Delete refuses an empty prefix (`store.delete_prefix`), so a bug can never wipe the bucket
- Background indexing failure -> status `failed` with the error, not an infinite spinner

## Verification
- Test files: `services/api/tests/test_videos.py`, `services/api/tests/test_videos_service.py`
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: `pnpm verify` green; every lifecycle verb has a route and a UI control

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [File Browser](file-browser.md)
- [App Workflows](../app-workflows.md)
