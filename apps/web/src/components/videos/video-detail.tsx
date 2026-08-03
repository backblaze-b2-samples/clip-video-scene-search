"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Film,
  Layers,
  Loader2,
  Pencil,
  Sparkles,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { StatusBadge } from "@/components/videos/status-badge";
import { SceneGrid } from "@/components/videos/scene-grid";
import { ApiError } from "@/lib/api-client";
import {
  useBuildSceneIndex,
  useDeleteVideo,
  useRenameVideo,
  useVideo,
} from "@/lib/queries";
import { formatDuration } from "@/lib/scene-format";

export function VideoDetail({ id }: { id: string }) {
  const router = useRouter();
  const { data: video, isLoading, error, refetch } = useVideo(id);
  const renameMutation = useRenameVideo();
  const deleteMutation = useDeleteVideo();
  const indexMutation = useBuildSceneIndex();

  const [renameOpen, setRenameOpen] = useState(false);
  const [renameValue, setRenameValue] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-24 w-full" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="aspect-video w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !video) {
    return (
      <ErrorState
        error={error}
        title="Couldn't load this video"
        onRetry={() => refetch()}
      />
    );
  }

  const isIndexing = video.status === "indexing";
  const isIndexed = video.status === "indexed";
  const progressLabel =
    video.scene_count > 0
      ? `${video.embedded_count}/${video.scene_count} scenes embedded`
      : "No scenes to index";

  const openRename = () => {
    setRenameValue(video.title);
    setRenameOpen(true);
  };

  const submitRename = () => {
    const title = renameValue.trim();
    if (!title) return;
    renameMutation.mutate(
      { id, title },
      {
        onSuccess: () => {
          toast.success("Video renamed");
          setRenameOpen(false);
        },
        onError: (err) =>
          toast.error(err instanceof ApiError ? err.message : "Rename failed"),
      },
    );
  };

  const confirmDelete = () => {
    deleteMutation.mutate(id, {
      onSuccess: () => {
        toast.success(`Deleted "${video.title}"`);
        router.push("/library");
      },
      onError: (err) =>
        toast.error(err instanceof ApiError ? err.message : "Delete failed"),
      onSettled: () => setDeleteOpen(false),
    });
  };

  const buildIndex = () => {
    indexMutation.mutate(id, {
      onSuccess: () =>
        toast.success("Building scene index…", {
          description: "Embedding keyframes with CLIP. This page updates as it runs.",
        }),
      onError: (err) =>
        toast.error(err instanceof ApiError ? err.message : "Couldn't start indexing"),
    });
  };

  return (
    <div className="space-y-6">
      <Link
        href="/library"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
        Back to Library
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="page-title truncate">{video.title}</h1>
            <StatusBadge status={video.status} />
          </div>
          <p className="mt-1.5 text-sm text-muted-foreground">
            {video.scene_count} scenes · {formatDuration(video.duration_seconds)} ·
            threshold {video.scene_threshold} · index model {video.clip_model}
          </p>
          {video.status === "failed" && video.error && (
            <p className="mt-2 text-sm text-[var(--attention)]">
              Indexing failed: {video.error}
            </p>
          )}
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={openRename}>
            <Pencil className="h-3.5 w-3.5" />
            Rename
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setDeleteOpen(true)}
          >
            <Trash2 className="h-3.5 w-3.5" />
            Delete
          </Button>
          <Button size="sm" onClick={buildIndex} disabled={isIndexing || indexMutation.isPending}>
            {isIndexing || indexMutation.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Sparkles className="h-3.5 w-3.5" />
            )}
            {isIndexed ? "Rebuild scene index" : "Build scene index"}
          </Button>
        </div>
      </div>

      {isIndexing && (
        <Card>
          <CardContent className="flex items-center gap-3 p-4 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            <span aria-live="polite">
              Embedding keyframes with CLIP — {progressLabel}. Weights download on
              first run; this can take a little longer the first time.
            </span>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="border-b border-border py-4 px-5">
          <CardTitle className="card-title flex items-center gap-2">
            <Layers className="h-4 w-4" aria-hidden="true" />
            Scenes
          </CardTitle>
        </CardHeader>
        <CardContent className="p-5">
          {video.scenes.length === 0 ? (
            <EmptyState
              icon={Film}
              title="No scenes detected"
              description="PySceneDetect found no scenes in this video."
            />
          ) : (
            <SceneGrid scenes={video.scenes} />
          )}
        </CardContent>
      </Card>

      {/* Edit (rename) — single free-text field, pre-filled, no default hint. */}
      <Dialog open={renameOpen} onOpenChange={setRenameOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename video</DialogTitle>
            <DialogDescription>
              Update the title shown in the Library and search results.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="rename-title">Title</Label>
            <Input
              id="rename-title"
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  submitRename();
                }
              }}
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setRenameOpen(false)}
              disabled={renameMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={submitRename}
              disabled={renameMutation.isPending || !renameValue.trim()}
            >
              {renameMutation.isPending ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete — confirm dialog held open until the mutation settles. */}
      <AlertDialog open={deleteOpen} onOpenChange={(open) => !open && setDeleteOpen(false)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete video?</AlertDialogTitle>
            <AlertDialogDescription className="break-words">
              This permanently deletes <strong>{video.title}</strong> and every
              scene clip, keyframe, and embedding under its prefixes, then
              rebuilds the search index. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={(event) => {
                event.preventDefault();
                confirmDelete();
              }}
              disabled={deleteMutation.isPending}
              className={buttonVariants({ variant: "destructive" })}
            >
              {deleteMutation.isPending ? "Deleting…" : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
