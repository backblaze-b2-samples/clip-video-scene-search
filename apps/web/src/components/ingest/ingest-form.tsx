"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Clapperboard, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { ApiError, createVideo } from "@/lib/api-client";

// Finite-option fields are selectors (never free text); Title is the only
// free-text field and its safe default (the file name) is surfaced as a
// placeholder/description hint — never an autofill button.
const THRESHOLDS = [
  { value: "20", label: "20 — more, finer scenes" },
  { value: "27", label: "27 — balanced (default)" },
  { value: "35", label: "35 — fewer, coarser scenes" },
];
const CLIP_MODELS = [
  {
    value: "ViT-B-32/laion2b_s34b_b79k",
    label: "ViT-B-32 (laion2b) — fast, ~600 MB (default)",
  },
  {
    value: "ViT-L-14/laion2b_s32b_b82k",
    label: "ViT-L-14 (laion2b) — higher quality, larger",
  },
];

const ingestSchema = z.object({
  title: z.string().max(200).optional(),
  scene_threshold: z.enum(["20", "27", "35"]),
  clip_model: z.enum([
    "ViT-B-32/laion2b_s34b_b79k",
    "ViT-L-14/laion2b_s32b_b82k",
  ]),
});

type IngestValues = z.infer<typeof ingestSchema>;

function baseName(filename: string): string {
  return filename.replace(/\.[^./]+$/, "");
}

export function IngestForm() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<number | null>(null);

  const form = useForm<IngestValues>({
    resolver: zodResolver(ingestSchema),
    defaultValues: {
      title: "",
      scene_threshold: "27",
      clip_model: "ViT-B-32/laion2b_s34b_b79k",
    },
  });

  const submitting = progress !== null;
  const titlePlaceholder = file
    ? baseName(file.name)
    : "Defaults to the video file name";

  const onSubmit = async (values: IngestValues) => {
    if (!file) {
      toast.error("Choose a video file to ingest first.");
      return;
    }
    setProgress(0);
    try {
      const video = await createVideo(
        file,
        {
          title: values.title?.trim() || baseName(file.name),
          scene_threshold: values.scene_threshold,
          clip_model: values.clip_model,
        },
        (pct) => setProgress(pct),
      );
      toast.success(`Segmented "${video.title}" into ${video.scene_count} scenes`, {
        description: "Next: open the video and click “Build scene index”.",
      });
      router.push(`/videos/${video.id}`);
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.message : "Failed to ingest the video";
      toast.error(detail);
      setProgress(null);
    }
  };

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Ingest a video</CardTitle>
      </CardHeader>
      <CardContent className="p-5">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <div className="space-y-2">
              <FormLabel htmlFor="video-file">Video file</FormLabel>
              <Input
                id="video-file"
                ref={inputRef}
                type="file"
                accept="video/*"
                disabled={submitting}
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <FormDescription>
                The source is uploaded to B2, then split into scenes with
                PySceneDetect (a clip + keyframe per scene). No CLIP model runs
                yet — embedding happens later, on demand.
              </FormDescription>
            </div>

            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Title</FormLabel>
                  <FormControl>
                    <Input placeholder={titlePlaceholder} {...field} />
                  </FormControl>
                  <FormDescription>
                    A human-readable name for the library. Leave blank to use the
                    file name.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="scene_threshold"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Detection threshold</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger className="w-full sm:w-80">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {THRESHOLDS.map((t) => (
                        <SelectItem key={t.value} value={t.value}>
                          {t.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    PySceneDetect content threshold. Lower detects more cuts; 27
                    is a good default for most footage.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="clip_model"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>CLIP model</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger className="w-full sm:w-80">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {CLIP_MODELS.map((m) => (
                        <SelectItem key={m.value} value={m.value}>
                          {m.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    Embedding model used when you build the scene index. Weights
                    download on first use; ViT-B-32 is the smaller, faster
                    default.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {progress !== null && (
              <div className="space-y-1.5" aria-live="polite">
                <Progress value={progress} />
                <p className="text-xs text-muted-foreground">
                  {progress < 100
                    ? `Uploading… ${progress}%`
                    : "Segmenting scenes on the server…"}
                </p>
              </div>
            )}

            <div className="flex justify-end">
              <Button type="submit" disabled={submitting || !file}>
                {submitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Clapperboard className="h-4 w-4" />
                )}
                {submitting ? "Ingesting…" : "Ingest & segment"}
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
