import { VideoDetail } from "@/components/videos/video-detail";

export default async function VideoDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div className="animate-fade-in">
      <VideoDetail id={id} />
    </div>
  );
}
