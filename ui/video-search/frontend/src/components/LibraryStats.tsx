import { Film, Clock, Calendar, Sparkles } from "lucide-react";
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
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-primary/5 rounded-lg p-4 flex items-center gap-3">
            <Skeleton className="w-5 h-5 rounded" />
            <div className="space-y-1.5">
              <Skeleton className="h-6 w-14" />
              <Skeleton className="h-3 w-20" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  const durationLabel = stats.total_duration_hours >= 1
    ? `${stats.total_duration_hours}h`
    : `${stats.total_duration_minutes}m`;

  const items = [
    {
      icon: Film,
      value: String(stats.total_videos),
      label: "Videos indexed",
    },
    {
      icon: Clock,
      value: durationLabel,
      label: "Content searchable",
    },
    {
      icon: Calendar,
      value: `${stats.earliest_year}\u2013${stats.latest_year}`,
      label: "Archive span",
    },
    {
      icon: Sparkles,
      value: String(stats.total_categories),
      label: "AI categories",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {items.map(({ icon: Icon, value, label }) => (
        <div key={label} className="bg-primary/5 border border-primary/10 rounded-lg p-4 flex items-center gap-3">
          <Icon className="w-5 h-5 text-primary flex-shrink-0" />
          <div>
            <p className="font-mono text-xl font-semibold tracking-tight text-foreground">
              {value}
            </p>
            <p className="text-[11px] text-muted-foreground">{label}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
