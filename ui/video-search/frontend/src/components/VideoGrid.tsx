import { useState, useEffect } from "react";
import { Search, SlidersHorizontal } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { VideoCard } from "./VideoCard";
import type { VideoResult } from "@/types";

const PAGE_SIZE = 12;

interface VideoGridProps {
  results: VideoResult[] | null;
  isLoading: boolean;
  onPlay: (videoId: string, segmentIndex: number) => void;
  onFindSimilar?: (videoId: string) => void;
  onClearFilters?: () => void;
}

export function VideoGrid({
  results,
  isLoading,
  onPlay,
  onFindSimilar,
  onClearFilters,
}: VideoGridProps) {
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [results]);

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="space-y-2">
            <Skeleton className="aspect-video rounded-lg" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        ))}
      </div>
    );
  }

  if (results === null || (results.length === 0 && !onClearFilters)) {
    return (
      <div className="text-center py-16 space-y-3">
        <Search className="w-12 h-12 text-muted-foreground/40 mx-auto" />
        <p className="text-muted-foreground">
          No videos in the library yet
        </p>
        <p className="text-xs text-muted-foreground/60">
          Add videos from Archive.org to get started
        </p>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="text-center py-16 space-y-3">
        <SlidersHorizontal className="w-12 h-12 text-muted-foreground/40 mx-auto" />
        <p className="text-muted-foreground">
          No videos match your current filters
        </p>
        <p className="text-xs text-muted-foreground/60">
          Try adjusting your filters or broadening your search
        </p>
        {onClearFilters && (
          <Button variant="outline" size="sm" onClick={onClearFilters}>
            Clear all filters
          </Button>
        )}
      </div>
    );
  }

  const visibleResults = results.slice(0, visibleCount);
  const hasMore = results.length > visibleCount;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        {visibleResults.map((video) => (
          <VideoCard key={video.video_id} video={video} onPlay={onPlay} onFindSimilar={onFindSimilar} />
        ))}
      </div>
      {hasMore && (
        <div className="flex justify-center pt-4">
          <Button
            variant="outline"
            onClick={() => setVisibleCount((prev) => prev + PAGE_SIZE)}
          >
            Load more ({results.length - visibleCount} remaining)
          </Button>
        </div>
      )}
    </div>
  );
}
