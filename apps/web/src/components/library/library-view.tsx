"use client";

import Link from "next/link";
import {
  Clapperboard,
  Film,
  HardDrive,
  Layers,
  Video as VideoIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { StatusBadge } from "@/components/videos/status-badge";
import { useLibrarySummary, useVideos } from "@/lib/queries";
import { formatDuration } from "@/lib/scene-format";
import { formatDate } from "@/lib/utils";

function SummaryStrip() {
  const { data: summary, isLoading } = useLibrarySummary();
  const cards = [
    { title: "Videos", value: summary?.total_videos ?? 0, icon: VideoIcon },
    { title: "Scenes", value: summary?.total_scenes ?? 0, icon: Film },
    {
      title: "Indexed scenes",
      value: summary?.embedded_scenes ?? 0,
      icon: Layers,
    },
    {
      title: "App storage",
      value: summary?.total_bytes_human ?? "0 B",
      icon: HardDrive,
    },
  ];
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.title} className="card-hover">
          <CardHeader className="flex flex-row items-center justify-between pt-4 pb-2 px-4 space-y-0">
            <CardTitle className="text-xs font-semibold text-muted-foreground">
              {card.title}
            </CardTitle>
            <div className="stat-icon-wrap">
              <card.icon className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pb-5 px-4">
            {isLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <div className="stat-value">{card.value}</div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export function LibraryView() {
  const { data: videos = [], isLoading, error, refetch } = useVideos();

  return (
    <div className="space-y-6">
      <SummaryStrip />

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4 space-y-0">
          <CardTitle className="card-title">Video library</CardTitle>
          <Button asChild size="sm" className="h-8 shrink-0">
            <Link href="/ingest">
              <Clapperboard className="h-3.5 w-3.5" />
              Ingest video
            </Link>
          </Button>
        </CardHeader>
        <CardContent className="p-3">
          {isLoading ? (
            <div className="space-y-2 p-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-14 w-full" />
              ))}
            </div>
          ) : error ? (
            <ErrorState
              error={error}
              title="Couldn't load the library"
              onRetry={() => refetch()}
              className="px-4"
            />
          ) : videos.length === 0 ? (
            <EmptyState
              icon={Film}
              title="No videos yet"
              description="Ingest a video to segment it into searchable scenes, or run the seed script."
              action={
                <Button asChild size="sm">
                  <Link href="/ingest">
                    <Clapperboard className="h-3.5 w-3.5" />
                    Ingest video
                  </Link>
                </Button>
              }
              className="px-4"
            />
          ) : (
            <ul className="divide-y divide-border">
              {videos.map((video) => (
                <li key={video.id}>
                  <Link
                    href={`/videos/${video.id}`}
                    className="flex items-center justify-between gap-3 rounded-md px-3 py-3 hover:bg-muted/60"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium">{video.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {video.scene_count} scenes ·{" "}
                        {formatDuration(video.duration_seconds)} ·{" "}
                        {formatDate(video.created_at)}
                      </p>
                    </div>
                    <StatusBadge status={video.status} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
