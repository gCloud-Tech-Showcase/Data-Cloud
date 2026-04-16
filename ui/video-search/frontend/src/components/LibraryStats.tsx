import { Film, Layers, Calendar } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { LibraryStats as Stats } from "@/types";

interface LibraryStatsProps {
  stats: Stats | null;
}

export function LibraryStats({ stats }: LibraryStatsProps) {
  if (!stats) return null;

  return (
    <div className="space-y-4">
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
                {stats.earliest_year}–{stats.latest_year}
              </p>
              <p className="text-xs text-muted-foreground">Year range</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {stats.categories.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted-foreground">Collection:</span>
          {stats.categories.map((cat) => (
            <Badge key={cat.name} variant="outline" className="gap-1">
              {cat.name}
              <span className="text-muted-foreground">{cat.count}</span>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
