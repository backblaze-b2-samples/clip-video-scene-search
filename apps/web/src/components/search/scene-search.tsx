"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import {
  Clapperboard,
  ImageIcon,
  Library,
  Loader2,
  Play,
  Search,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState } from "@/components/ui/empty-state";
import { ApiError, searchByImage, searchByText } from "@/lib/api-client";
import { formatScore, timecodeRange } from "@/lib/scene-format";
import type { SearchResponse } from "@clip-video-scene-search/shared";

function SearchResults({ result }: { result: SearchResponse }) {
  if (result.hits.length === 0) {
    return (
      <EmptyState
        icon={Search}
        title="No matching scenes"
        description="Nothing matched this query. Build the scene index for your videos, or try a different description."
        action={
          <div className="flex flex-wrap items-center justify-center gap-2">
            <Button asChild size="sm">
              <Link href="/ingest">
                <Clapperboard className="h-3.5 w-3.5" />
                Ingest video
              </Link>
            </Button>
            <Button asChild size="sm" variant="outline">
              <Link href="/library">
                <Library className="h-3.5 w-3.5" />
                Go to Library
              </Link>
            </Button>
          </div>
        }
      />
    );
  }
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {result.hits.map((hit) => (
        <div
          key={`${hit.video_id}-${hit.scene_number}`}
          className="overflow-hidden rounded-lg border border-border bg-card"
        >
          <div className="relative aspect-video bg-muted">
            {hit.keyframe_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={hit.keyframe_url}
                alt={`${hit.video_title} scene ${hit.scene_number}`}
                className="h-full w-full object-cover"
                loading="lazy"
              />
            )}
            <span className="absolute right-2 top-2">
              <Badge className="bg-primary text-primary-foreground">
                {formatScore(hit.score)} match
              </Badge>
            </span>
          </div>
          <div className="space-y-1 px-3 py-2">
            <Link
              href={`/videos/${hit.video_id}`}
              className="block truncate text-sm font-medium hover:underline"
              title={hit.video_title}
            >
              {hit.video_title}
            </Link>
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-xs text-muted-foreground tabular-nums">
                #{hit.scene_number} ·{" "}
                {timecodeRange(hit.start_timecode, hit.end_timecode)}
              </span>
              {hit.clip_url && (
                <a
                  href={hit.clip_url}
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
        </div>
      ))}
    </div>
  );
}

export function SceneSearch() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [searching, setSearching] = useState(false);
  const imageInputRef = useRef<HTMLInputElement>(null);

  const runTextSearch = async () => {
    const q = query.trim();
    if (!q) return;
    setSearching(true);
    try {
      setResult(await searchByText(q));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Search failed");
    } finally {
      setSearching(false);
    }
  };

  const runImageSearch = async (file: File) => {
    setSearching(true);
    try {
      setResult(await searchByImage(file));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Image search failed");
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="p-5">
          <Tabs defaultValue="text" onValueChange={() => setResult(null)}>
            <TabsList>
              <TabsTrigger value="text">
                <Search className="h-3.5 w-3.5" />
                Text
              </TabsTrigger>
              <TabsTrigger value="image">
                <ImageIcon className="h-3.5 w-3.5" />
                Image
              </TabsTrigger>
            </TabsList>

            <TabsContent value="text" className="mt-4">
              <div className="flex flex-col gap-2 sm:flex-row">
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      runTextSearch();
                    }
                  }}
                  placeholder="e.g. a person walking on a beach"
                  aria-label="Text query"
                />
                <Button onClick={runTextSearch} disabled={searching || !query.trim()}>
                  {searching ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Search className="h-4 w-4" />
                  )}
                  Search
                </Button>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                CLIP encodes your text into the same space as the scene keyframes
                and ranks scenes by cosine similarity.
              </p>
            </TabsContent>

            <TabsContent value="image" className="mt-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                <Input
                  ref={imageInputRef}
                  type="file"
                  accept="image/*"
                  disabled={searching}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) runImageSearch(file);
                  }}
                  aria-label="Query image"
                />
                {searching && (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                )}
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                Upload a still image to find visually similar scenes.
              </p>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {result === null ? (
        <EmptyState
          icon={Search}
          title="Search your indexed scenes"
          description="Describe a scene, or upload a reference image, to find matching moments across your video library."
        />
      ) : (
        <SearchResults result={result} />
      )}
    </div>
  );
}
