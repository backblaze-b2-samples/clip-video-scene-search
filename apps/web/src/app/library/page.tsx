import { LibraryView } from "@/components/library/library-view";

export default function LibraryPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Library</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Your video-scene corpus on Backblaze B2 — sources, scene clips,
          keyframes, and embeddings the app owns. For the raw bucket contents,
          use the Files explorer.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <LibraryView />
      </div>
    </div>
  );
}
