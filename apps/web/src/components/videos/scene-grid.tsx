import { Film, Play } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { timecodeRange } from "@/lib/scene-format";
import type { Scene } from "@clip-video-scene-search/shared";

/** Grid of scene keyframes with timecodes and a link to each scene clip. */
export function SceneGrid({ scenes }: { scenes: Scene[] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {scenes.map((scene) => (
        <div
          key={scene.number}
          className="overflow-hidden rounded-lg border border-border bg-card"
        >
          <div className="relative aspect-video bg-muted">
            {scene.keyframe_url ? (
              // Presigned B2 URL (expires); plain img avoids next/image re-fetch
              // of a signed URL.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={scene.keyframe_url}
                alt={`Scene ${scene.number} keyframe`}
                className="h-full w-full object-cover"
                loading="lazy"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-muted-foreground">
                <Film className="h-6 w-6" aria-hidden="true" />
              </div>
            )}
            <span className="absolute left-2 top-2">
              <Badge variant="secondary">Scene {scene.number}</Badge>
            </span>
            {scene.embedded && (
              <span className="absolute right-2 top-2">
                <Badge className="bg-[var(--success)] text-white hover:bg-[var(--success)]">
                  indexed
                </Badge>
              </span>
            )}
          </div>
          <div className="flex items-center justify-between gap-2 px-3 py-2">
            <span className="font-mono text-xs text-muted-foreground tabular-nums">
              {timecodeRange(scene.start_timecode, scene.end_timecode)}
            </span>
            {scene.clip_url && (
              <a
                href={scene.clip_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
              >
                <Play className="h-3 w-3" aria-hidden="true" />
                Open clip
              </a>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
