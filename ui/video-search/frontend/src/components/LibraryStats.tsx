import { Film, Layers, Calendar } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { LibraryStats as Stats } from "@/types";

interface LibraryStatsProps {
  stats: Stats | null;
  isLoading?: boolean;
}

export function LibraryStats({ stats, isLoading = false }: LibraryStatsProps) {
  if (!stats && !isLoading) return null;

  if (!stats) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-4 flex items-center gap-3">
              <Skeleton className="w-5 h-5 rounded" />
              <div className="space-y-1.5">
                <Skeleton className="h-7 w-16" />
                <Skeleton className="h-3 w-12" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <Card>
        <CardContent className="p-4 flex items-center gap-3">
          <Film className="w-5 h-5 text-primary" />
          <div>
            <p className="font-mono text-2xl font-semibold tracking-tight">
              {stats.total_videos}
            </p>
            <p className="text-xs text-muted-foreground">Videos</p>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4 flex items-center gap-3">
          <Layers className="w-5 h-5 text-primary" />
          <div>
            <p className="font-mono text-2xl font-semibold tracking-tight">
              {stats.total_embeddings.toLocaleString()}
            </p>
            <p className="text-xs text-muted-foreground">Embeddings</p>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4 flex items-center gap-3">
          <Calendar className="w-5 h-5 text-primary" />
          <div>
            <p className="font-mono text-2xl font-semibold tracking-tight">
              {stats.earliest_year}&ndash;{stats.latest_year}
            </p>
            <p className="text-xs text-muted-foreground">Year range</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
