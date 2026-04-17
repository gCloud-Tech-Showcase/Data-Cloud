import { useState, useCallback, useEffect } from "react";
import { Header } from "@/components/Header";
import { SearchBar } from "@/components/SearchBar";
import { VideoGrid } from "@/components/VideoGrid";
import { VideoPlayer } from "@/components/VideoPlayer";
import { LibraryStats } from "@/components/LibraryStats";
import { AddVideos } from "@/components/AddVideos";
import { FilterSidebar } from "@/components/FilterSidebar";
import { Button } from "@/components/ui/button";
import { Search, Plus } from "lucide-react";
import {
  searchVideos,
  getSegmentPlayUrl,
  getLibraryStats,
  listVideos,
  findSimilar,
} from "@/lib/api";
import type {
  VideoResult,
  SearchResponse,
  LibraryStats as StatsType,
} from "@/types";

type View = "library" | "add";

export default function App() {
  const [view, setView] = useState<View>("library");
  const [allVideos, setAllVideos] = useState<VideoResult[]>([]);
  const [searchResult, setSearchResult] = useState<SearchResponse | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<StatsType | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [searchLabel, setSearchLabel] = useState<string | undefined>();
  const [externalQuery, setExternalQuery] = useState<string | undefined>();
  const [activeFilters, setActiveFilters] = useState<Record<string, string | null>>({});

  // Player state
  const [playerVideo, setPlayerVideo] = useState<VideoResult | null>(null);
  const [playerUrl, setPlayerUrl] = useState<string | null>(null);
  const [activeSegment, setActiveSegment] = useState(0);

  // Load stats and all videos on mount
  useEffect(() => {
    getLibraryStats().then(setStats).catch(() => {}).finally(() => setStatsLoading(false));
    loadAllVideos();
  }, []);

  async function loadAllVideos() {
    try {
      const { videos } = await listVideos();
      setAllVideos(
        videos.map((v) => ({
          ...v,
          category: v.category ?? null,
          ai_description: v.ai_description ?? null,
          best_distance: 0,
          relevance_pct: 0,
          matching_intervals: 0,
          top_segments: [],
        }))
      );
    } catch {
      // silently fail
    }
  }

  const handleSearch = useCallback(async (query: string) => {
    setView("library");
    setIsLoading(true);
    setError(null);
    setSearchLabel(undefined);
    setHasSearched(true);
    try {
      const result = await searchVideos(query);
      setSearchResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setSearchResult(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleClearSearch = useCallback(() => {
    setSearchResult(null);
    setHasSearched(false);
    setSearchLabel(undefined);
    setExternalQuery("");
  }, []);

  const handleFindSimilar = useCallback(async (videoId: string) => {
    setView("library");
    setIsLoading(true);
    setError(null);
    setHasSearched(true);
    const video = allVideos.find((v) => v.video_id === videoId);
    setSearchLabel(`Videos similar to "${video?.title || videoId}"`);
    setExternalQuery("");
    try {
      const result = await findSimilar(videoId);
      setSearchResult({
        query: `similar:${videoId}`,
        results: result.results,
        total_results: result.total_results,
        search_time_ms: result.search_time_ms,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to find similar");
      setSearchResult(null);
    } finally {
      setIsLoading(false);
    }
  }, [allVideos]);

  const handlePlay = useCallback(
    (videoId: string, segmentIndex: number) => {
      const results = hasSearched ? searchResult?.results : allVideos;
      const video = results?.find((v) => v.video_id === videoId);
      if (!video) return;

      setPlayerVideo(video);
      setPlayerUrl(getSegmentPlayUrl(videoId, segmentIndex));
      setActiveSegment(segmentIndex);
    },
    [hasSearched, allVideos, searchResult]
  );

  const handleSegmentChange = useCallback(
    (segmentIndex: number) => {
      if (!playerVideo) return;
      setPlayerUrl(getSegmentPlayUrl(playerVideo.video_id, segmentIndex));
      setActiveSegment(segmentIndex);
    },
    [playerVideo]
  );

  const handleFilterChange = useCallback((field: string, value: string | null) => {
    setActiveFilters((prev) => ({ ...prev, [field]: value }));
  }, []);

  const handleClearAllFilters = useCallback(() => {
    setActiveFilters({});
  }, []);

  // Show search results if searched, otherwise show all videos
  const unfilteredVideos = hasSearched
    ? searchResult?.results ?? null
    : allVideos.length > 0
      ? allVideos
      : null;

  // Apply multi-field filters
  const displayedVideos = unfilteredVideos
    ? unfilteredVideos.filter((v) => {
        for (const [field, value] of Object.entries(activeFilters)) {
          if (value === null) continue;
          const videoValue = (v as unknown as Record<string, unknown>)[field];
          if (videoValue !== value) return false;
        }
        return true;
      })
    : null;

  const hasFilters = stats?.filters && Object.values(stats.filters).some((f) => f.length > 0);

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <Header />

      <main className="flex-1 w-full max-w-7xl mx-auto p-4 md:p-6 lg:p-8 space-y-6">
        {/* Stats */}
        <LibraryStats stats={stats} isLoading={statsLoading} />

        {/* View tabs */}
        <div className="flex items-center gap-2 border-b border-border pb-2">
          <Button
            variant={view === "library" ? "default" : "ghost"}
            size="sm"
            className="gap-1.5"
            onClick={() => setView("library")}
          >
            <Search className="w-4 h-4" />
            Library
          </Button>
          <Button
            variant={view === "add" ? "default" : "ghost"}
            size="sm"
            className="gap-1.5"
            onClick={() => setView("add")}
          >
            <Plus className="w-4 h-4" />
            Add videos
          </Button>
        </div>

        {/* Library view */}
        {view === "library" && (
          <div className="space-y-6">
            <SearchBar
              onSearch={handleSearch}
              onClear={handleClearSearch}
              isLoading={isLoading}
              externalQuery={externalQuery}
            />

            {searchLabel && !isLoading && (
              <p className="text-sm font-medium text-foreground">
                {searchLabel}
              </p>
            )}

            {error && (
              <div className="bg-destructive/10 border border-destructive/20 text-destructive rounded-lg p-4 text-sm">
                {error}
              </div>
            )}

            <div className={`flex gap-6 ${hasFilters ? "" : ""}`}>
              {/* Filter sidebar */}
              {hasFilters && stats?.filters && (
                <FilterSidebar
                  filters={stats.filters}
                  activeFilters={activeFilters}
                  onFilterChange={handleFilterChange}
                  onClearAll={handleClearAllFilters}
                />
              )}

              {/* Video grid */}
              <div className="flex-1 min-w-0">
                <VideoGrid
                  results={displayedVideos}
                  isLoading={isLoading}
                  searchTime={hasSearched ? searchResult?.search_time_ms : undefined}
                  query={hasSearched ? searchResult?.query : undefined}
                  onPlay={handlePlay}
                  onFindSimilar={handleFindSimilar}
                />
              </div>
            </div>
          </div>
        )}

        {/* Add videos view */}
        {view === "add" && <AddVideos />}
      </main>

      {playerVideo && playerUrl && (
        <VideoPlayer
          videoId={playerVideo.video_id}
          title={playerVideo.title}
          videoUrl={playerUrl}
          segments={playerVideo.top_segments}
          activeSegment={activeSegment}
          totalDuration={playerVideo.duration_total_seconds}
          onSegmentChange={handleSegmentChange}
          onClose={() => {
            setPlayerVideo(null);
            setPlayerUrl(null);
          }}
        />
      )}
    </div>
  );
}
