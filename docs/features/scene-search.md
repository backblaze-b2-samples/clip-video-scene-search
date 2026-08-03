<!-- last_verified: 2026-08-03 -->
# Feature: Scene Search

## Purpose
Answer text-to-scene and image-to-scene queries over the indexed video library.

## Used By
- UI: `/search` page (`components/search/scene-search.tsx`)
- API: `POST /search/text`, `POST /search/image`

## Core Functions
- `services/api/app/service/search.py` — `search_text()`, `search_image()`, `_load_index()`, `_hits_from()`
- `services/api/app/runtime/search.py` — HTTP handlers (text is JSON; image is multipart)
- `apps/web/src/components/search/scene-search.tsx` — text box + image upload + results grid
- `apps/web/src/lib/api-client.ts` — `searchByText()`, `searchByImage()`

## Canonical Files
- Search service: `services/api/app/service/search.py`

## Inputs
- Text: `{ query: string, top_k?: number }`
- Image: multipart file + optional `top_k` query param

## Outputs
- `SearchResponse`: mode (`text` | `image`), query, top_k, hits[]
- Each `SearchHit`: video id + title, scene number, start/end timecode, score, presigned keyframe_url and clip_url

## Flow
- Load `index.faiss` + `mapping.json` from B2; if absent, return empty hits (no CLIP call)
- Embed the query with OpenCLIP (`embed_text` / `embed_image`)
- `search_index()` returns `(row, score)` pairs; each row maps to a scene, presigning its keyframe and clip
- The UI renders a grid: keyframe thumbnail, match percentage, video title (links to the video), scene # + timecode, "Open clip"

## Edge Cases
- Empty corpus / no index yet -> `hits: []`, HTTP 200 (never an error)
- Empty text query -> 422 (validation)
- Oversized image upload -> 413

## UX States
- Empty (no search yet): a prompt to describe a scene or upload an image
- Loading: spinner on the search button / image input
- Results: grid of scene cards; "No matching scenes" when hits are empty

## Verification
- Test files: `services/api/tests/test_search.py` (empty corpus, hit mapping, empty-query 422, image path)
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: `pnpm verify` green; empty corpus returns empty hits without touching CLIP

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [FAISS Scene Index](faiss-scene-index.md)
- [App Workflows](../app-workflows.md)
