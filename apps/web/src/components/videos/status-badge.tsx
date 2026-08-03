import { Badge } from "@/components/ui/badge";
import type { VideoStatus } from "@clip-video-scene-search/shared";

const LABELS: Record<string, string> = {
  segmented: "Segmented",
  indexing: "Indexing…",
  indexed: "Indexed",
  failed: "Failed",
};

/**
 * Lifecycle badge for a Video. `indexed` reads as success, `failed` as
 * destructive, `indexing` as an in-progress accent, `segmented` as neutral.
 */
export function StatusBadge({ status }: { status: VideoStatus }) {
  const label = LABELS[status] ?? status;
  if (status === "indexed") {
    return (
      <Badge className="bg-[var(--success)] text-white hover:bg-[var(--success)]">
        {label}
      </Badge>
    );
  }
  if (status === "failed") {
    return <Badge variant="destructive">{label}</Badge>;
  }
  if (status === "indexing") {
    return (
      <Badge variant="secondary" className="animate-pulse">
        {label}
      </Badge>
    );
  }
  return <Badge variant="outline">{label}</Badge>;
}
