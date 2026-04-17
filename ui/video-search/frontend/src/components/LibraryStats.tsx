import { Film, Layers, Calendar } from "lucide-react";
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
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="bg-primary/5 rounded-lg p-4 flex items-center gap-3">
            <Skeleton className="w-5 h-5 rounded" />
            <div className="space-y-1.5">
              <Skeleton className="h-7 w-16" />
              <Skeleton className="h-3 w-12" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  const items = [
    { icon: Film, value: stats.total_videos, label: "Videos" },
    { icon: Layers, value: stats.total_embeddings.toLocaleString(), label: "Embeddings" },
    { icon: Calendar, value: `${stats.earliest_year}\u2013${stats.latest_year}`, label: "Year range" },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      {items.map(({ icon: Icon, value, label }) => (
        <div key={label} className="bg-primary/5 border border-primary/10 rounded-lg p-4 flex items-center gap-3">
          <Icon className="w-5 h-5 text-primary" />
          <div>
            <p className="font-mono text-xl font-semibold tracking-tight text-foreground">
              {value}
            </p>
            <p className="text-xs text-muted-foreground">{label}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
