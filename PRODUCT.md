# Product

## Register

The primary entity is a **Video** — a source video in the library — and the **scenes** derived from it (each a clip, a keyframe, and a CLIP embedding). Everything the product does revolves around ingesting, indexing, searching, and managing videos and their scenes on Backblaze B2.

## Users

Video-platform engineers and ML dataset curators who already store video on Backblaze
B2 and want a multimodal search layer over it. Their context: raw video is opaque —
finding "the beach shot" means scrubbing timelines by hand. They want a pipeline that
turns a video library into scene-indexed, searchable content without standing up a
vector database or paying a per-call vision API.

## Product Purpose

A sample app that turns a raw video library on Backblaze B2 into a scene-indexed,
visually searchable asset with no external API dependency. PySceneDetect splits each
video into scenes; a bundled ffmpeg cuts a clip and keyframe per scene; OpenCLIP embeds
each keyframe; and a FAISS index plus JSON metadata are written back to B2. A search UI
answers text-to-scene and image-to-scene queries. It demonstrates sustained multimodal
write to B2 (one video → many clips, keyframes, and embeddings) with B2 as the sole
storage layer, accessed only through the S3-compatible API. Success = a builder can
clone it, add B2 credentials (the only secret), ingest a video, build its scene index
on local CPU, and search it — trusting every screen enough to build on top.

## Brand Personality

Confident, precise, quietly professional. Voice is direct and free of hype ("Stop
wiring boilerplate and start building"). The interface should feel like a modern
developer tool — considered, calm, trustworthy — not a marketing showpiece. It is a
**neutral foundation** that others rebrand: the design carries craft through restraint,
not through a strong opinionated identity of its own.

## Anti-references

- **Generic AI/SaaS slop.** No gradient text, hero-metric templates, identical
  icon-card grids, tracked uppercase eyebrows, or decorative glassmorphism. These are
  the exact 2026 AI tells this kit exists to help builders avoid.
- **Over-branded / loud.** No heavy brand-color drenching, decorative motion, or flashy
  effects. It is scaffolding to be rebranded, not a hero page.
- **Toy / prototype feel.** No missing states, inconsistent components, or placeholder
  polish. Must read as production-grade.
- **Enterprise-drab.** No Bootstrap-era gray boxes or dense-but-lifeless admin-panel
  look. Considered, like modern dev tools (Linear, GitHub Primer, Stripe).

## Design Principles

- **Practice what you preach.** The kit itself must model the production quality it
  asks agents to produce. Slop here propagates into every project built on it.
- **Neutral foundation, easy to rebrand.** Identity lives in tokens (`globals.css`) and
  one config file. Screens are built from the shared UI kit so a rebrand is a token
  swap, not a rewrite.
- **Earned familiarity over novelty.** Use standard, trusted affordances (top bar +
  side nav, command palette, data tables). The tool disappears into the task.
- **Every state is designed.** Default, hover, focus, active, disabled, loading (skeleton),
  empty (teaches the interface), and error (says what's wrong + offers retry) — never
  half-shipped.
- **Consistency is the feature.** One button vocabulary, one form-control set, one icon
  style across every screen. Divergence is a bug.

## Accessibility & Inclusion

Target **WCAG 2.1 AA**. Body text ≥ 4.5:1, large/bold text ≥ 3:1, visible focus
indicators on every interactive element, full keyboard navigation, correct semantic
landmarks and heading order, labelled form controls, and a `prefers-reduced-motion`
alternative for every animation. Full light and dark theme parity.
