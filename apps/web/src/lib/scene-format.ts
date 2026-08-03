/** Formatting helpers for scene timecodes, durations, and similarity scores. */

/** Seconds -> "M:SS" (or "H:MM:SS" past an hour). */
export function formatDuration(seconds: number | null | undefined): string {
  if (
    seconds === null ||
    seconds === undefined ||
    !Number.isFinite(seconds) ||
    seconds < 0
  )
    return "—";
  const total = Math.round(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const mm = h > 0 ? String(m).padStart(2, "0") : String(m);
  const ss = String(s).padStart(2, "0");
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

/** Trim a "HH:MM:SS.mmm" timecode to whole seconds for compact display. */
export function shortTimecode(tc: string): string {
  return tc.split(".")[0] ?? tc;
}

/** Cosine similarity (-1..1) -> a 0-100% match string. */
export function formatScore(score: number): string {
  const pct = Math.round(Math.max(0, Math.min(1, score)) * 100);
  return `${pct}%`;
}

/** "start – end" compact timecode range. */
export function timecodeRange(start: string, end: string): string {
  return `${shortTimecode(start)} – ${shortTimecode(end)}`;
}
