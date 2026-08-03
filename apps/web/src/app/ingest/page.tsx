import { IngestForm } from "@/components/ingest/ingest-form";

export default function IngestPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Ingest</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Upload a video to split it into scenes with PySceneDetect. Each scene
          gets its own clip and a keyframe, stored on Backblaze B2. Build the
          scene index afterwards to make it searchable.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2 max-w-2xl">
        <IngestForm />
      </div>
    </div>
  );
}
