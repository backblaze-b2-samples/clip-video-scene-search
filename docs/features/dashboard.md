<!-- last_verified: 2026-08-03 -->
# Feature: Dashboard

## Purpose
Give an at-a-glance overview of the scene-indexed video library and recent activity.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /library/summary`, `GET /videos`, `GET /files/stats/activity`

## Core Functions
- `apps/web/src/components/dashboard/scene-stats-cards.tsx` — library stat cards (videos, scenes, indexed scenes, app storage)
- `apps/web/src/components/dashboard/recent-videos-table.tsx` — the most recent videos, each linking to its detail page
- `apps/web/src/components/dashboard/upload-chart.tsx` — daily B2 write activity (object creations) as a bar chart
- `apps/web/src/lib/queries.ts` — `useLibrarySummary()`, `useVideos()`, `useUploadActivity()`
- `services/api/app/service/library.py` — `summarize()` business logic
- `services/api/app/runtime/videos.py` — `GET /library/summary` handler

## Canonical Files
- Stats source: `services/api/app/service/library.py`
- Dashboard layout: `apps/web/src/app/page.tsx`

## Inputs
- None (loads automatically)

## Outputs
- `GET /library/summary` -> `LibrarySummary` (total_videos, segmented/indexed videos, total/embedded scenes, source/scene bytes, index_present)
- `GET /videos` -> `Video[]` for the recent-videos table (newest-first)
- `GET /files/stats/activity?days=7` -> `DailyUploadCount[]` for the write-activity chart

## Flow
- Page loads -> stat cards read `/library/summary`, the table reads `/videos`, the chart reads the bucket activity endpoint
- Cards show videos, scenes, indexed scenes, and total app storage across the app's B2 prefixes
- The recent-videos table shows title (links to `/videos/[id]`), scene count, length, status badge, and added date

## Edge Cases
- API unavailable -> inline error state with Retry
- No videos yet -> empty stat values and an empty-state table prompting Ingest
- Large libraries -> the summary walks the app prefixes; costs scale with the app's own object count, not the whole bucket

## UX States
- Loading: skeletons on cards, table, and chart
- Empty: zeroed cards and "No videos yet"
- Loaded: populated cards, chart, and table

## Verification
- Test files: `services/api/tests/test_videos.py` (`/library/summary`), `apps/web/src/lib/queries.test.ts`
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: `pnpm verify` green; cards and table reflect the seeded/ingested videos

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Video Library](video-library.md)
- [App Workflows](../app-workflows.md)
