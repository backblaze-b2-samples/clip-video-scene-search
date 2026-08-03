<!-- last_verified: 2026-08-03 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Dashboard with library metrics and recent videos
  - Scene Search (text-to-scene + image-to-scene)
  - Ingest (upload + segment), Library (sample-scoped asset view), Video detail (scenes, rename, delete, build index)
  - Generic Files explorer and Upload page (kept from the starter)
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - Video lifecycle REST API (list, create/segment, detail, rename, delete, build index)
  - Text/image scene search over a FAISS index
  - B2 S3 integration via boto3 (confined to `repo/`)
  - PySceneDetect segmentation, bundled-ffmpeg clip/keyframe extraction, OpenCLIP embedding, FAISS indexing (all lazy-imported)
  - Health check, structured JSON logging, Prometheus-format metrics
- **packages/shared/** — TypeScript type definitions mirroring the Pydantic models

## Backend Layering

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access & external adapters (boto3 B2 client, CLIP, FAISS, ffmpeg, PySceneDetect)
  |
service/   Business logic — orchestrates repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer — verified by `tests/test_structure.py`
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Each file stays under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (Video, Scene, SearchHit, LibrarySummary, ...)
    config/                Settings (B2_* + CLIP/scene settings); endpoint derived from region
    repo/                  Adapters (data access layer)
      b2_client.py         Cached custom-UA S3 client + health
      b2_object.py         On-demand object body reads
      store.py             Generic B2 object ops for the scene corpus (put/get/list/json/delete_prefix/presign)
      scene_detect.py      PySceneDetect ContentDetector wrapper (lazy import)
      video_ffmpeg.py      Bundled ffmpeg (imageio-ffmpeg) clip cut + keyframe extract
      clip.py              OpenCLIP embed_image/embed_text; CUDA -> MPS -> CPU device autodetect (lazy)
      faiss_index.py       IndexFlatIP build/search + .npy (de)serialize; 1 OpenMP thread (lazy)
      list_cache.py        Full-bucket listing cache (stale-while-revalidate)
      counter.py           Durable download counter
    service/               Business logic
      videos.py            Meta store + prefix scheme + model conversion
      ingest.py            create (segment) / run_index (embed + FAISS) / rebuild / delete / rename
      search.py            search_text / search_image over the FAISS index
      library.py           Sample-scoped footprint over the app's own prefixes
      files.py, upload.py, metadata.py   Generic file browser / upload (kept)
    runtime/               FastAPI route handlers (videos, search, files, upload, health, metrics)
  scripts/export_openapi.py
  tests/                   pytest (structural + route contract + scene-index unit)
scripts/seed_sample_video.py   Offline, deterministic, idempotent demo seed
```

### ML crash guards (macOS arm64)

- `repo/__init__.py` sets `KMP_DUPLICATE_LIB_OK=TRUE` before any native library loads (torch + faiss each bundle an OpenMP runtime).
- `repo/faiss_index.py` additionally caps faiss to a single OpenMP thread — the env var alone is not enough.
- torch / open_clip / faiss / scenedetect are imported **inside functions**, so app import and the structural/contract tests never pull the native stack and no weights download at build time.

## B2 object layout (single bucket)

```
videos/<id>/source.<ext>          source video
videos/<id>/meta.json             video + scene metadata (status: segmented | indexing | indexed | failed)
scenes/clips/<id>/<n>.mp4         per-scene clips
scenes/keyframes/<id>/<n>.jpg     per-scene keyframes
scenes/embed/<id>/<n>.npy         per-keyframe CLIP vectors (L2-normalized float32)
scenes/index/index.faiss          global FAISS IndexFlatIP
scenes/index/mapping.json         row -> scene mapping
```

Every delete is prefix-scoped: `store.delete_prefix` refuses an empty prefix, and a video delete only ever targets that video's own prefixes, then rebuilds the index.

## Data Stores

- **Backblaze B2** — the sole data store (S3-compatible API). No application database: per-video metadata, embeddings, and the FAISS index all live as objects.

## External Services

- **Backblaze B2 S3 API** — storage, retrieval, deletion, presigned URLs. No other external service and no second API key — PySceneDetect, ffmpeg, OpenCLIP, and FAISS all run on-device.

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full documentation.

- **Frontend -> API** — CORS-restricted to configured origins; `CORSMiddleware` is registered LAST in `main.py` (outermost) so it wraps every response, including uncaught-exception 500s. A per-IP rate-limit middleware sits inner to CORS.
- **API -> B2** — authenticated via application keys, signature v4; the S3 endpoint is derived from `B2_REGION`.
- **Client -> B2** — presigned URLs for keyframe thumbnails and scene-clip playback.

## Data Flows

- **Ingest (create)**: Browser -> `POST /videos` (multipart) -> service uploads source -> PySceneDetect segments -> per scene cut clip + keyframe -> B2 -> meta.json `status=segmented`
- **Build scene index (run)**: Browser -> `POST /videos/{id}/index` (returns immediately, status `indexing`) -> background: OpenCLIP embeds each keyframe -> `.npy` to B2 -> FAISS index + mapping rebuilt -> `status=indexed`; the UI polls `GET /videos/{id}`
- **Search**: Browser -> `POST /search/text` or `POST /search/image` -> OpenCLIP embeds the query -> cosine over the FAISS index -> hits with presigned keyframe/clip URLs
- **Delete**: Browser -> `DELETE /videos/{id}` -> prefix-scoped delete of every asset -> index rebuilt

## API Contract

- Checked-in OpenAPI artifact: `docs/api/openapi.json`
- Export/check command: `pnpm contract:export` / `pnpm contract:check`
- FastAPI freshness test: `services/api/tests/test_openapi_contract.py`
- Frontend route drift test: `apps/web/src/lib/api-contract.test.ts`

## Canonical Files

- Layered route handler: `services/api/app/runtime/videos.py`
- Service orchestration: `services/api/app/service/ingest.py`
- B2 data access (repo layer): `services/api/app/repo/store.py`, `services/api/app/repo/b2_client.py`
- CLIP/FAISS adapters: `services/api/app/repo/clip.py`, `services/api/app/repo/faiss_index.py`
- Pydantic models: `services/api/app/types/videos.py`, `services/api/app/types/search.py`
- Config: `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (also the catch-all that converts uncaught exceptions to a typed JSON 500)
- `/metrics` (Prometheus format) and `/health` (B2 connectivity check)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
