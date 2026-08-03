<!-- last_verified: 2026-08-03 -->
# Feature: CLIP Embedding

## Purpose
Embed scene keyframes (and search queries) into a shared vector space with OpenCLIP so scenes can be ranked by similarity.

## Used By
- API: `POST /videos/{id}/index` (embeds every keyframe, in the background)
- API: `POST /search/text`, `POST /search/image` (embeds the query)

## Core Functions
- `services/api/app/repo/clip.py` — `select_device()`, `embed_image()`, `embed_text()`, `active_device()`
- `services/api/app/service/ingest.py` — `run_index()` embeds keyframes; `services/api/app/service/search.py` embeds queries

## Canonical Files
- CLIP adapter: `services/api/app/repo/clip.py`

## Inputs
- image bytes (keyframe or uploaded still) or text (query string)
- settings: `CLIP_MODEL` ("<arch>/<pretrained>", default `ViT-B-32/laion2b_s34b_b79k`) — a single **global** deploy setting, not a per-video choice, so every vector shares one dimensionality for the one shared FAISS index; `CLIP_DEVICE` (empty = autodetect)

## Outputs
- A 1-D L2-normalized float32 vector (numpy) — cosine similarity is a plain dot product on these
- Side effect (indexing): the vector is stored as `scenes/embed/<id>/<n>.npy`

## Flow
- torch / open_clip are imported lazily inside functions; the model, preprocess transform, and tokenizer are loaded once and cached
- Device selection is explicit override -> CUDA -> Apple MPS -> CPU, defaulting to CPU. A GPU is never hard-required.
- Weights download on the first real embed (the "Build scene index" action), never at build/import

## Edge Cases
- No GPU present -> CPU is used automatically; ViT-B-32 embeds a handful of keyframes in seconds
- Library without MPS support -> falls back CUDA -> CPU (documented per-sample)
- Model download failure during background indexing -> the video's status is set to `failed` with the error

## UX States
- Surfaced via the video status (`indexing` -> `indexed` / `failed`) and per-scene "indexed" badges

## Verification
- Test files: `services/api/tests/test_search.py` (empty corpus returns before any CLIP import), `services/api/tests/test_scene_index.py`
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: `pnpm verify` green without downloading weights (lazy imports hold)

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [FAISS Scene Index](faiss-scene-index.md)
- [Scene Search](scene-search.md)
