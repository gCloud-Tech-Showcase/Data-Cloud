import { useState, useCallback, useEffect, useMemo } from "react";
import { Header } from "@/components/Header";
import { SearchBar } from "@/components/SearchBar";
import { VideoGrid } from "@/components/VideoGrid";
import { VideoPlayer } from "@/components/VideoPlayer";
import { LibraryStats } from "@/components/LibraryStats";
import { AddVideos } from "@/components/AddVideos";
import { FilterSidebar } from "@/components/FilterSidebar";
import { ResultsBar } from "@/components/ResultsBar";
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
  const [activeFilters, setActiveFilters] = useState<Record<string, Set<string>>>({});
  const [sortBy, setSortBy] = useState("title");

  // Player state
  const [playerVideo, setPlayerVideo] = useState<VideoResult | null>(null);
  const [playerUrl, setPlayerUrl] = useState<string | null>(null);
  const [activeSegment, setActiveSegment] = useState(0);

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
          mood: v.mood ?? null,
          color_mode: v.color_mode ?? null,
          style: v.style ?? null,
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
    setSortBy("relevance");
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
    setSortBy("title");
  }, []);

  const handleFindSimilar = useCallback(async (videoId: string) => {
    setView("library");
    setIsLoading(true);
    setError(null);
    setHasSearched(true);
    setSortBy("relevance");
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

  // Multi-select filter toggle
  const handleFilterChange = useCallback((field: string, value: string) => {
    setActiveFilters((prev) => {
      const current = prev[field] || new Set<string>();
      const next = new Set(current);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return { ...prev, [field]: next };
    });
  }, []);

  const handleClearAllFilters = useCallback(() => {
    setActiveFilters({});
  }, []);

  // Unfiltered results
  const unfilteredVideos = hasSearched
    ? searchResult?.results ?? null
    : allVideos.length > 0
      ? allVideos
      : null;

  // Apply multi-select filters
  const filteredVideos = useMemo(() => {
    if (!unfilteredVideos) return null;
    return unfilteredVideos.filter((v) => {
      for (const [field, values] of Object.entries(activeFilters)) {
        if (values.size === 0) continue;
        const videoValue = (v as unknown as Record<string, unknown>)[field];
        if (typeof videoValue !== "string" || !values.has(videoValue)) return false;
      }
      return true;
    });
  }, [unfilteredVideos, activeFilters]);

  // Sort
  const displayedVideos = useMemo(() => {
    if (!filteredVideos) return null;
    const sorted = [...filteredVideos];
    switch (sortBy) {
      case "title":
        sorted.sort((a, b) => (a.title || "").localeCompare(b.title || ""));
        break;
      case "title-desc":
        sorted.sort((a, b) => (b.title || "").localeCompare(a.title || ""));
        break;
      case "year-desc":
        sorted.sort((a, b) => (b.year || 0) - (a.year || 0));
        break;
      case "year-asc":
        sorted.sort((a, b) => (a.year || 0) - (b.year || 0));
        break;
      case "relevance":
        sorted.sort((a, b) => a.best_distance - b.best_distance);
        break;
    }
    return sorted;
  }, [filteredVideos, sortBy]);

  const hasFilters = stats?.filters && Object.values(stats.filters).some((f) => f.length > 0);
  const hasActiveFilters = Object.values(activeFilters).some((s) => s.size > 0);

  return (
    <div className="min-h-screen bg-muted/40 text-foreground flex flex-col">
      <Header />

      <main className="flex-1 w-full max-w-7xl mx-auto p-4 md:p-6 lg:p-8 space-y-6">
        <LibraryStats stats={stats} isLoading={statsLoading} />

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

        {view === "library" && (
          <div className="space-y-4">
            <div className="bg-background rounded-xl border border-border p-6 shadow-sm">
              <SearchBar
                onSearch={handleSearch}
                onClear={handleClearSearch}
                isLoading={isLoading}
                externalQuery={externalQuery}
              />
            </div>

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

            <div className="flex gap-6">
              {hasFilters && stats?.filters && (
                <FilterSidebar
                  filters={stats.filters}
                  activeFilters={activeFilters}
                  onFilterChange={handleFilterChange}
                  onClearAll={handleClearAllFilters}
                />
              )}

              <div className="flex-1 min-w-0 space-y-4">
                {displayedVideos && (
                  <ResultsBar
                    totalResults={displayedVideos.length}
                    searchTime={hasSearched ? searchResult?.search_time_ms : undefined}
                    query={hasSearched ? searchResult?.query : undefined}
                    sortBy={sortBy}
                    onSortChange={setSortBy}
                  />
                )}

                <VideoGrid
                  results={displayedVideos}
                  isLoading={isLoading}
                  onPlay={handlePlay}
                  onFindSimilar={handleFindSimilar}
                  onClearFilters={hasActiveFilters ? handleClearAllFilters : undefined}
                />
              </div>
            </div>
          </div>
        )}

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
