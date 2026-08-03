import { SceneSearch } from "@/components/search/scene-search";

export default function SearchPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Scene Search</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Find scenes across your video library by text or by example image.
          Results carry a keyframe thumbnail, timecode, and a link to the scene
          clip on Backblaze B2.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <SceneSearch />
      </div>
    </div>
  );
}
