import { Search } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { VideoCard } from "./VideoCard";
import type { VideoResult } from "@/types";

interface VideoGridProps {
  results: VideoResult[] | null;
  isLoading: boolean;
  searchTime?: number;
  query?: string;
  onPlay: (videoId: string, segmentIndex: number) => void;
  onFindSimilar?: (videoId: string) => void;
}

export function VideoGrid({
  results,
  isLoading,
  searchTime,
  query,
  onPlay,
  onFindSimilar,
}: VideoGridProps) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="aspect-video rounded-lg" />
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (results === null) {
    return (
      <div className="text-center py-16 space-y-3">
        <Search className="w-12 h-12 text-muted-foreground/40 mx-auto" />
        <p className="text-muted-foreground">
          Search for videos by describing what you're looking for
        </p>
        <p className="text-xs text-muted-foreground/60">
          Try concepts like "friendship", "chase scene", or "educational health film"
        </p>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="text-center py-16 space-y-3">
        <Search className="w-12 h-12 text-muted-foreground/40 mx-auto" />
        <p className="text-muted-foreground">
          No videos found for "{query}"
        </p>
        <p className="text-xs text-muted-foreground/60">
          Try a different description or explore one of the suggested topics
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {searchTime !== undefined && (
        <p className="text-sm text-muted-foreground">
          {results.length} video{results.length !== 1 ? "s" : ""} found
          <span className="ml-1 text-muted-foreground/60">
            ({searchTime}ms)
          </span>
        </p>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {results.map((video) => (
          <VideoCard key={video.video_id} video={video} onPlay={onPlay} onFindSimilar={onFindSimilar} />
        ))}
      </div>
    </div>
  );
}
