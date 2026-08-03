import Link from "next/link";
import { Clapperboard, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { SceneStatsCards } from "@/components/dashboard/scene-stats-cards";
import { RecentVideosTable } from "@/components/dashboard/recent-videos-table";
import { UploadChart } from "@/components/dashboard/upload-chart";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Your scene-indexed video library on Backblaze B2 at a glance.
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild size="sm" variant="outline" className="h-8">
            <Link href="/search">
              <Search className="h-3.5 w-3.5" />
              Scene search
            </Link>
          </Button>
          <Button asChild size="sm" className="h-8">
            <Link href="/ingest">
              <Clapperboard className="h-3.5 w-3.5" />
              Ingest video
            </Link>
          </Button>
        </div>
      </div>
      <SceneStatsCards />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="animate-fade-in-up stagger-3">
          <UploadChart />
        </div>
        <div className="animate-fade-in-up stagger-4">
          <RecentVideosTable />
        </div>
      </div>
    </div>
  );
}
