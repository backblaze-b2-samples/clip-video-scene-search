<!-- last_verified: 2026-08-03 -->
# App Workflows

User journeys inside the application.

## Ingest a Video (create)

- User navigates to `/ingest`
- Chooses a video file, optionally sets a **Title** (a free-text field; the placeholder shows the default derived from the file name), and picks a **Detection threshold** (20 / 27 / 35) and a **CLIP model** from selectors — finite-option fields are never free text
- On submit the source uploads to B2 with a progress bar, then the row switches to "Segmenting scenes on the server…"
- The server runs PySceneDetect, and for each scene cuts a clip and extracts a keyframe (bundled ffmpeg), uploading each to B2
- On success a toast reports the scene count and the user is taken to the video detail page with status **Segmented**
- No CLIP model runs yet — embedding is deferred to "Build scene index"
- See: [Scene Detection](features/scene-detection.md), [Scene Clips & Keyframes](features/scene-clips-keyframes.md)

## Build the Scene Index (run — the marquee action)

- On a video's detail page (`/videos/[id]`), the user clicks **Build scene index**
- The request returns immediately with status **Indexing…**; the page polls and shows `N/total scenes embedded`
- In the background OpenCLIP embeds each keyframe (downloading the model on first use), stores a `.npy` vector per keyframe, and rebuilds the global FAISS index + mapping in B2
- When done the status becomes **Indexed** and each scene shows an "indexed" badge; if it fails, the status becomes **Failed** with the error, rather than spinning forever
- See: [CLIP Embedding](features/clip-embedding.md), [FAISS Scene Index](features/faiss-scene-index.md)

## Search Scenes

- User navigates to `/search`
- **Text tab**: types a description ("a person walking on a beach") and searches; CLIP encodes the text and ranks scenes by cosine similarity
- **Image tab**: uploads a still image to find visually similar scenes
- Results are a grid of matching scenes: keyframe thumbnail, a match percentage, video title (links to the video), scene number + timecode range, and an "Open clip" link to the scene clip in B2
- An empty corpus (nothing indexed yet) returns "No matching scenes", never an error
- See: [Scene Search](features/scene-search.md)

## Manage a Video (read / edit / delete)

- **Read**: the Library lists every video; the detail page shows all scenes as keyframe thumbnails with timecodes and clip links
- **Edit (rename)**: the Rename dialog opens pre-filled with the current title; saving updates the Library and search-result titles
- **Delete**: a confirmation dialog stays open showing "Deleting…" until the request settles, then every scene clip, keyframe, and embedding under the video's prefixes is removed and the search index is rebuilt
- See: [Video Library](features/video-library.md)

## Browse the Library vs the Bucket

- `/library` is the **sample-scoped** view: a summary strip (videos, scenes, indexed scenes, app storage) plus the list of videos the app owns
- `/files` is the generic **full-bucket** explorer kept from the starter — it shows every object in the bucket (including the app's own `videos/` and `scenes/` prefixes), with preview, download, and delete
- `/upload` is the generic raw-upload page, complementary to Ingest
- See: [Video Library](features/video-library.md), [File Browser](features/file-browser.md)

## View Dashboard

- User navigates to `/` (home)
- Stat cards summarize the library (videos, scenes, indexed scenes, app storage) from `GET /library/summary`
- A recent-videos table links each row to its detail page; a B2 write-activity chart shows daily object creation
- See: [Dashboard](features/dashboard.md)

## Change Preferences

- User navigates to `/settings`
- A banner states the page is mostly a demonstration: only **Theme** is wired up for real; the Profile/preference fields persist to `localStorage` only and drive no behaviour
- See: [Settings](features/settings.md)
