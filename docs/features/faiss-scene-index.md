<!-- last_verified: 2026-08-03 -->
# Feature: FAISS Scene Index

## Purpose
Maintain a single global index of every embedded keyframe so scene search is a fast cosine ranking.

## Used By
- API: `POST /videos/{id}/index` (rebuild after embedding), `DELETE /videos/{id}` (rebuild after removal)
- API: `POST /search/text`, `POST /search/image` (query the index)

## Core Functions
- `services/api/app/repo/faiss_index.py` — `build_index()`, `search_index()`, `to_npy_bytes()`, `from_npy_bytes()`
- `services/api/app/service/ingest.py` — `rebuild_index()` collects embedded vectors and writes the index

## Canonical Files
- FAISS adapter: `services/api/app/repo/faiss_index.py`

## Inputs
- vectors: list of L2-normalized float32 vectors (read from `scenes/embed/**`)
- query vector + top_k (search)

## Outputs
- B2 objects: `scenes/index/index.faiss` (serialized `IndexFlatIP`) and `scenes/index/mapping.json` (row -> scene mapping)
- Search returns `(row, score)` pairs, best first, mapped back to scene metadata

## Flow
- `IndexFlatIP` over normalized vectors is exact cosine ranking; one vector per keyframe (not per-patch), so no MaxSim needed
- faiss is imported lazily and pinned to a single OpenMP thread (`omp_set_num_threads(1)`) in addition to the `KMP_DUPLICATE_LIB_OK` env guard — the env var alone does not prevent the torch+faiss dual-OpenMP abort on macOS arm64
- `rebuild_index()` reads persisted `.npy` vectors (not in-memory state), so it is correct after a delete as well as after a run; an empty corpus clears the index

## Edge Cases
- Empty corpus -> the index/mapping objects are removed; search returns empty hits
- top_k larger than the corpus -> clamped to the number of vectors
- `build_index([])` -> ValueError (callers guard on an empty corpus first)

## UX States
- Surfaced indirectly via the Library summary (`index_present`, indexed scene count) and search results

## Verification
- Test files: `services/api/tests/test_scene_index.py` (build, ranking, top_k clamp, .npy round-trip; skipped when faiss is not installed)
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: with faiss installed, the nearest vector ranks first and scores are descending

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [CLIP Embedding](clip-embedding.md)
- [Scene Search](scene-search.md)
