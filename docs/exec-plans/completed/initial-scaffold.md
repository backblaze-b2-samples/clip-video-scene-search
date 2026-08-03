# Build plan — `clip-video-scene-search`

> Source of truth for the starter tree: `.claude/scratch/vcsk-5f751598-7f47-4599-bb22-a0d6c33657b3/`
> (fresh clone of `vibe-coding-starter-kit`). All keep/trim/add deltas are computed against it.
> This is a **re-build**: a prior attempt cosmetically renamed the sibling
> `clip-visual-product-search` (an e-commerce CLIP product-image search) and was interrupted.
> **Do NOT reuse the product/catalog/e-commerce domain** (products, categories, currencies,
> product-form, catalog-gallery, seed-catalog). Build the ACTUAL PySceneDetect video-scene
> pipeline from the starter kit.

## 1. Purpose

`clip-video-scene-search` turns a raw video library on B2 into a **scene-indexed, visually
searchable asset** with no external API dependency. For each source video, **PySceneDetect**
(`ContentDetector`) splits it into scenes; per scene the app cuts a scene clip and extracts one
representative keyframe (via bundled ffmpeg); **CLIP/OpenCLIP** embeds each keyframe; and a
**FAISS** scene index + JSON metadata are written back to B2. A search UI answers
**text-to-scene** ("a person walking on a beach") and **image-to-scene** (upload a still)
queries, returning matching scenes with keyframe thumbnail, start/end timecode, and a link to
the scene clip in B2.

Audience: video-platform engineers and ML dataset curators who already store video on B2 and
want a multimodal search layer over it. It demonstrates **sustained multimodal write** (one
video → many clips + keyframes + embeddings; a 1-hour video → hundreds of B2 objects) and B2 as
the storage layer for a full multimodal indexing pipeline, accessed only through the
S3-compatible API with a custom user agent and standard `B2_*` env vars. Runs on local OSS —
B2 credentials are the only secret; no second API key.

## 2. Architecture delta from `vibe-coding-starter-kit`

The starter kit is a generic Next.js (`apps/web`) + FastAPI (`services/api`) file dashboard
backed by B2. It is the ceiling — strip what this app doesn't need, keep the platform, add the
video-scene pipeline. This mirrors the proven layout of the passing sibling `colpali-pdf-search`
(FAISS + local embedding search): **do not read or clone that sibling** — the concrete structure
it validated is encoded below so the builder works only from the starter kit + this plan.

### KEEP (as-is or lightly rebranded)
- The entire platform skeleton: `apps/web` (Next 15 + Tailwind + shadcn/ui, theme provider,
  sidebar/header/command-palette, design-system page, query-client, api-client), all
  `components/ui/*`, `lib/*`, hooks, tests.
- `services/api` platform: `main.py` (lifespan validation, JSON logging, CORS/rate-limit/timing
  middleware ordering — **do not reorder**), `app/config`, `app/repo/b2_client.py` +
  `b2_object.py` (cached custom-UA S3 client, list cache), `app/runtime/{health,files,upload,metrics}`,
  `app/service/{files,upload,metadata}`, `app/types/*`, the pytest suite, `scripts/*`,
  `.github/workflows/ci.yml`, `pre-commit`, `pyproject.toml`.
- **Bucket explorer (NON-NEGOTIABLE keep):** the full-bucket browse at `/files`
  (`components/files/*`, `runtime/files.py`, `service/files.py`). It stays even though the app is
  scene-centric — it's the generic "see everything in the bucket" view. *Note:* this app also adds
  a sample-scoped **Library** (below); the two coexist exactly as they do in `colpali-pdf-search`
  (generic `/files` + domain `/library`).
- Generic `/upload` page — kept (raw upload to the bucket; complements domain Ingest).

### TRIM (remove from starter)
- No product/e-commerce domain exists in the starter, so nothing of that kind to remove — but the
  builder must **not introduce** any (guard against accidentally pulling from the renamed sibling).
- Doc/feature files that no longer apply: `docs/features/metadata-extraction.md`,
  `docs/features/file-upload.md` (repurpose/replace — see §5). Starter dashboard copy about
  "file management" is rewritten, not kept verbatim.
- `PRODUCT.md` / `GEMINI.md` / `AGENTS.md` marketing/identity copy referencing the starter kit is
  rebranded (identifiers per §6); no separate e-commerce copy is added.

### ADD (new for `clip-video-scene-search`)
Backend (`services/api/app`), mirroring the colpali split (cheap step on create, heavy embed on run):
- `config/settings.py` — **rewrite to standard `B2_*` names** (see §6) + video/CLIP settings:
  `clip_model` (default `"ViT-B-32/laion2b_s34b_b79k"`), `clip_device` (empty = autodetect),
  `scene_threshold` (default `27.0`), `search_top_k` (default `12`), `min_scene_len_seconds`.
- `repo/__init__.py` — set `KMP_DUPLICATE_LIB_OK=TRUE` at import (torch + faiss dual-OpenMP crash
  guard; see risks) — copy the colpali-proven approach.
- `repo/store.py` — generic B2 object ops for the scene corpus (`put_bytes`, `list_prefix`,
  `read_json`, `write_json`, `delete_prefix` [non-empty prefix only], `presign_get`, `public_url`),
  reusing the cached custom-UA client from `b2_client`. boto3 stays confined to `repo/`.
- `repo/clip.py` — the ONLY place open_clip/torch load. `select_device()` = explicit override →
  **CUDA → MPS → CPU** (hard rule from `api-provider-selection.md`; never hard-require a GPU).
  Lazy imports so app import / structural tests never pull the multi-GB stack; weights download on
  first real use, never at build. `embed_image(bytes)->[dim] float32 L2-normalized`,
  `embed_text(str)->[dim] ...` via `open_clip.create_model_and_transforms` + tokenizer.
- `repo/scene_detect.py` — PySceneDetect wrapper: `open_video` + `SceneManager` +
  `ContentDetector(threshold=...)` → `get_scene_list()` (list of (start,end) FrameTimecodes with
  `.get_seconds()` / `.get_timecode()`).
- `repo/video_ffmpeg.py` — thin wrapper over the **bundled** ffmpeg binary
  (`imageio_ffmpeg.get_ffmpeg_exe()`; do NOT rely on a system/Homebrew ffmpeg): `cut_clip(src, start,
  end, out_mp4)` and `extract_keyframe(src, at_seconds, out_jpg)`.
- `repo/faiss_index.py` — single-vector cosine index: `IndexFlatIP` over L2-normalized keyframe
  vectors + a row→scene mapping. Simpler than colpali's MaxSim (one vector per keyframe, not
  per-patch). `build_index(scene_vectors)->(bytes, mapping)`, `search(index_bytes, mapping, qvec,
  top_k)`. faiss imported lazily and pinned to **one OpenMP thread** (`faiss.omp_set_num_threads(1)`).
- `service/videos.py` — Video entity meta store on B2 (prefixes in §3): `new_video_id`,
  `save_meta`/`load_meta`/`list_videos`/`validate_video_id`, prefix constants, `VideoNotFound`.
- `service/ingest.py` — **create** = download source from B2 → PySceneDetect segment → per scene:
  cut clip + extract keyframe → upload to B2 → write meta (`status="segmented"`, scene list with
  number, start/end seconds+timecode, keyframe key, clip key). **run** = embed every keyframe with
  CLIP → store per-keyframe `.npy` → rebuild the global scene index (`status="indexed"`). Persist
  per-scene progress to meta before/through the embed so a polling UI advances determinately (copy
  colpali's `run_indexing` progress pattern). `rebuild_index()` after run and after delete.
- `service/search.py` — `search_text(q, top_k)` and `search_image(bytes, top_k)`: embed query,
  cosine-rank against the B2 scene index, return hits (video id, scene, start/end timecode, score,
  keyframe presigned URL, clip presigned URL, video title). Empty corpus → empty hits, not error.
- `service/library.py` — sample-scoped asset listing over the app's own prefixes for the Library view.
- `runtime/videos.py` — routes: `GET /videos` (list), `POST /videos` (create: upload+segment),
  `GET /videos/{id}` (detail w/ scenes), `PATCH /videos/{id}` (**edit** = rename title),
  `DELETE /videos/{id}` (**delete** = scoped `delete_prefix` of every prefix for that id + rebuild),
  `POST /videos/{id}/index` (**run** = embed+index), keyframe/clip presign passthrough.
- `runtime/search.py` — `POST /search/text`, `POST /search/image` (multipart image upload).
- `types/videos.py`, `types/search.py` — pydantic response models (Video, Scene, SearchHit,
  SearchResponse), re-exported from `types/__init__.py`.
- `scripts/seed_sample_video.py` — **seed** (see §3): fully offline, deterministic, idempotent.
- `tests/` — structural/contract tests for the new routes + a scene-index unit test (no model download).

Frontend (`apps/web/src`):
- `lib/app-config.ts` — `APP_NAME = "CLIP Video Scene Search"`,
  `APP_DESCRIPTION = "Scene-indexed video search powered by Backblaze B2"`.
- Sidebar nav (`components/layout/app-sidebar.tsx`): Dashboard, **Scene Search** (`/search`),
  **Ingest** (`/ingest`), **Library** (`/library`), Files (`/files`, kept), Upload (`/upload`),
  Settings; Design under Reference. Update header `pageTitles` + UTM tag.
- Pages: `app/search/page.tsx` (text box + image-upload search; results = keyframe thumb +
  timecode + "Open clip" link), `app/ingest/page.tsx` (create form), `app/library/page.tsx`
  (video library — sample-scoped asset explorer), `app/videos/[id]/page.tsx` (video detail:
  scenes as keyframe thumbnails with timecodes + clip links; **edit** rename + **delete** +
  **run** "Build scene index" actions).
- Components: `components/search/*`, `components/ingest/*`, `components/library/*`,
  `components/videos/*`. Reuse `components/ui/*`, dropzone, empty/error states, query hooks.
- `lib/queries.ts` / `lib/api-client.ts` — add typed hooks/calls for the new endpoints.

## 3. B2 surface

All via the **S3-compatible API** (boto3), custom UA `b2ai-clip-video-scene-search`, confined to
`repo/`. **No b2-native API.** Endpoint derived from `B2_REGION` (no hardcoded region/endpoint).

App prefix scheme (single bucket, may be shared — every delete is prefix-scoped):
- `videos/<video_id>/source.<ext>` — source video (seeded or user-uploaded)
- `videos/<video_id>/meta.json` — video + scene metadata (title, status, scenes[])
- `scenes/clips/<video_id>/<scene>.mp4` — per-scene clips
- `scenes/keyframes/<video_id>/<scene>.jpg` — per-scene keyframes
- `scenes/embed/<video_id>/<scene>.npy` — per-keyframe CLIP vectors
- `scenes/index/index.faiss` + `scenes/index/mapping.json` — global scene index

S3 ops exercised: `put_object` (source, clips, keyframes, embeddings, index, mapping, meta),
`get_object` (source download for segmentation, embeddings/index/meta reads),
`list_objects_v2` (videos, scenes, embeddings, bucket + library explorers),
`delete_objects`/`delete_object` (scoped video delete), `head_bucket` (health),
`head_object` (file metadata), `generate_presigned_url` (stream keyframes + scene clips to browser).

**Seed** (`scripts/seed_sample_video.py`): idempotent (skip if a seed video already exists).
Generates a small **synthetic multi-scene clip** with the bundled ffmpeg — ~5 visually distinct
segments (different `testsrc`/`color`/pattern + text overlay, ~3s each) concatenated, so
`ContentDetector` reliably finds hard cuts with **no network and no licensing concern** (generated
content = CC0). Uploads the source, runs segmentation (cut clips + extract keyframes), and writes
`meta.json` with `status="segmented"` so the Library has rich content on first run. CLIP embedding
(the multi-GB download) is deferred to the user/verify clicking **Build scene index** — the only
heavy step, kept out of setup. A commented, documented alternative in the script header shows how to
ingest a small CC-BY clip (e.g. a Blender open-movie segment) instead, for a realistic demo.

## 4. Key features (README + `docs/features/<f>.md` stubs)

Every feature is **`deployment: local`** — the entire pipeline (PySceneDetect, ffmpeg, CLIP, FAISS)
runs on-device. **No external API provider, no second key** (the description explicitly says "no
external API dependency"). Per `api-provider-selection.md`, local heavy work inherits the
**CPU-default / GPU-autodetect** hard rule (override → CUDA → MPS → CPU). **Genblaze is NOT used** —
the description's stack (PySceneDetect + CLIP) names no Genblaze/`genblaze-*`/`genblaze-s3`, so
provider orchestration via the Genblaze SDK does not apply.

1. **Scene detection (PySceneDetect)** — `ContentDetector` splits each video into scenes; selectable
   threshold. `deployment: local`.
2. **Scene clips + keyframes (ffmpeg)** — per scene, cut a clip and extract one keyframe, written to
   B2. `deployment: local` (bundled ffmpeg via imageio-ffmpeg).
3. **CLIP keyframe embeddings + FAISS scene index** — OpenCLIP embeds each keyframe; a cosine FAISS
   index + JSON metadata are stored in B2. `deployment: local`; model `ViT-B-32/laion2b_s34b_b79k`
   (ungated, ~600MB), CPU-default; est. cost for one demo run: **$0** (no paid API; local compute
   + B2 storage only).
4. **Text-to-scene + image-to-scene search** — CLIP text/image encoder → cosine over the scene
   index; results carry keyframe, timecode, clip link. `deployment: local`.
5. **Video library + bucket explorer** — sample-scoped Library over the app prefixes plus the
   generic full-bucket Files explorer (kept from the starter).

### Primary-entity lifecycle (UI completeness)
Primary entity: **Video** (a source video in the library). All lifecycle verbs are in the UI —
nothing omitted (`omitted_ui_verbs` = empty):
- **create** — Ingest page: upload a video → segment (PySceneDetect + clips + keyframes), `status=segmented`.
- **read** — Library (video list) + Video detail (`/videos/[id]`: scenes as keyframe thumbnails,
  timecodes, clip links).
- **edit** — rename the video title (inline/dialog on the detail page; `PATCH /videos/{id}`).
- **delete** — remove a video and every scene/clip/keyframe/embedding under its prefixes, then
  rebuild the index (`DELETE /videos/{id}`).
- **run** — "Build scene index": embed keyframes with CLIP + (re)build the FAISS index,
  `status=indexed` (`POST /videos/{id}/index`). The marquee action; poll status to `indexed`.

### Form UX conventions
- **Ingest (create) form:** free-text field = **Title** (a name; no finite set) with a placeholder
  hint (default derived from the uploaded filename). **Selector** fields (finite value sets → shadcn
  `Select`, never free text): **Detection threshold** (e.g. 20 / 27 (default) / 35) and **CLIP model**
  (`ViT-B-32/laion2b` (default) / `ViT-L-14/laion2b`). Safe defaults surfaced as
  `FormDescription`/placeholder guidance only — **no autofill button**. Exemplar to match:
  `apps/web/src/components/settings/settings-form.tsx`.
- **Edit form (rename):** single free-text Title field, opens **pre-filled** with the current title;
  no default hints (real resource).

## 5. Doc transforms
- **README.md** — rewrite top-to-bottom for video scene search (no e-commerce/product copy):
  what it does, the ingest→segment→extract→embed→query workflow, why B2 is the storage layer,
  quickstart (`pnpm run setup`, fill `.env`, seed, run), the standard `B2_*` env vars, and the
  local CPU-default / GPU note. Preserve the starter's structure and script table.
- `docs/features/` — **keep + adapt:** `dashboard.md`, `file-browser.md`, `settings.md`.
  **Delete/replace:** `metadata-extraction.md`, `file-upload.md`.
  **Add stubs (from _template.md):** `scene-detection.md`, `scene-clips-keyframes.md`,
  `clip-embedding.md`, `faiss-scene-index.md`, `scene-search.md`, `video-library.md`.
- `ARCHITECTURE.md` — update the module map to the new `repo/`+`service/` layout and the B2 prefix scheme.
- `PRODUCT.md`, `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md` — rebrand identifiers
  and one-line purpose; no e-commerce copy.
- Move this plan to `docs/exec-plans/completed/initial-scaffold.md` on PASS (Phase 5).

## 6. Rename table
| Aspect | From (starter) | To |
|---|---|---|
| kebab / repo / dir | `vibe-coding-starter-kit` | `clip-video-scene-search` |
| product Title Case | `OSS Starter Kit` | `CLIP Video Scene Search` |
| `APP_DESCRIPTION` | `File management dashboard powered by Backblaze B2` | `Scene-indexed video search powered by Backblaze B2` |
| snake / py ids | `vibe_coding_starter_kit` / `oss_starter_kit` | `clip_video_scene_search` |
| package.json `name` (root + apps/web + packages/shared) | `*starter-kit*` | `clip-video-scene-search` (scope kept) |
| S3 user agent (`user_agent_extra`) | `b2ai-oss-start` | `b2ai-clip-video-scene-search` |
| UTM `utm_content` (sidebar footer + any link) | `b2ai-oss-start` | `b2ai-clip-video-scene-search` |
| Docker image tag / compose name (if any) | `*starter-kit*` | `clip-video-scene-search` |
| CI workflow name/slug | starter name | `clip-video-scene-search` |
| FastAPI `title` (main.py) | `OSS Starter Kit API` | `CLIP Video Scene Search API` |

### Env var rename (MUST — parent standard #3; starter deviates)
The starter uses non-standard names; rename everywhere they appear (`settings.py`, `main.py`
`REQUIRED_B2_SETTINGS`/`PLACEHOLDER_VALUES`, `.env.example`, README, docs). Adopt colpali's
region-derived endpoint (no hardcoded endpoint/region in source):
| Starter | Standard (this app) |
|---|---|
| `B2_ENDPOINT` | *(removed)* → derive from `B2_REGION` via a `b2_endpoint` property |
| `B2_KEY_ID` | `B2_APPLICATION_KEY_ID` |
| `B2_APPLICATION_KEY` | `B2_APPLICATION_KEY` (unchanged) |
| `B2_BUCKET_NAME` | `B2_BUCKET_NAME` (unchanged) |
| *(none)* | `B2_REGION` (added; endpoint derived) |
| `B2_PUBLIC_URL` | `B2_PUBLIC_URL_BASE` |

## 7. Dependencies (`services/api/requirements.txt`)
Keep the starter's lower-bound `>=` pin style (a regression test enforces it). Add, with bounded pins
(unpinned ML = false-green that breaks on clean install / at model load):
```
scenedetect[opencv-headless]>=0.6.4,<0.7.0   # PySceneDetect + headless OpenCV (no GUI deps)
imageio-ffmpeg>=0.5.0                          # bundled ffmpeg binary (no system/Homebrew ffmpeg)
open_clip_torch>=2.24.0,<3.0.0                 # CLIP text+image encoders
torch>=2.2.0,<2.9.0
torchvision>=0.17.0,<0.24.0                    # required by open_clip image transforms
faiss-cpu>=1.8.0,<2.0.0
numpy>=1.26.0,<2.0.0                            # held <2 for FAISS/torch arm64 compat
```
Regenerate `requirements.lock` per `docs/dev-workflows.md` after editing. Frontend adds no new
runtime deps beyond existing shadcn/ui primitives.

## 8. Standards compliance (parent CLAUDE.md) — reviewer gate
1. **S3-compatible API default** — boto3 only, confined to `repo/`; no b2-native SDK. ✅
2. **Custom UA on every S3 client** — `user_agent_extra="b2ai-clip-video-scene-search"` on the single
   cached client in `repo/b2_client.py`; `store.py`/`b2_object.py` reuse it. ✅
3. **Standard `B2_*` names** — `B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`,
   `B2_REGION`, `B2_PUBLIC_URL_BASE` (see §6). ✅

## 9. Known risks / gotchas (bake into the build)
- **torch + faiss dual-OpenMP crash** (macOS arm64): set `KMP_DUPLICATE_LIB_OK=TRUE` in
  `repo/__init__.py` AND cap faiss to `omp_set_num_threads(1)`. The env var alone is not enough.
- **Bundled ffmpeg only** — resolve via `imageio_ffmpeg.get_ffmpeg_exe()`; never assume a
  system/Homebrew ffmpeg (Homebrew's is slim). Pass its path explicitly to every ffmpeg subprocess.
- **Lazy ML imports** — torch/open_clip/faiss/scenedetect imported inside functions so app import
  (and structural/contract tests) never pulls the native stack and no weights download at build.
- **CPU is the default** — autodetect CUDA → MPS → CPU; never hard-require a GPU. `ViT-B-32` on CPU
  embeds a handful of keyframes in seconds.
- **Scoped deletes only** — `delete_prefix` refuses an empty prefix; video delete only ever targets
  that video's own prefixes.
- **Commit per increment** (builder): scaffold → ingest/segment pipeline → search API → UI → docs,
  so a death leaves a resumable partial tree.
