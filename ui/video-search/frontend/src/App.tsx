import { useState, useCallback, useEffect } from "react";
import { Header } from "@/components/Header";
import { SearchBar } from "@/components/SearchBar";
import { VideoGrid } from "@/components/VideoGrid";
import { VideoPlayer } from "@/components/VideoPlayer";
import { LibraryStats } from "@/components/LibraryStats";
import { AddVideos } from "@/components/AddVideos";
import { FilterBar } from "@/components/FilterBar";
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
  const [activeFilter, setActiveFilter] = useState<string | null>(null);

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
          best_distance: 0,
          relevance_pct: 0,
          matching_intervals: 0,
          top_segments: [],
        }))
      );
    } catch {
      // silently fail — browse just won't show
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

  // Show search results if searched, otherwise show all videos
  const unfilteredVideos = hasSearched
    ? searchResult?.results ?? null
    : allVideos.length > 0
      ? allVideos
      : null;

  // Apply category filter
  const displayedVideos = unfilteredVideos && activeFilter
    ? unfilteredVideos.filter((v) => {
        const title = v.title?.toLowerCase() || "";
        const filter = activeFilter.toLowerCase();
        if (filter === "other") {
          return !["popeye", "betty boop", "looney tunes", "bugs bunny", "merrie melodies", "superman"].some(
            (k) => title.includes(k)
          );
        }
        if (filter === "looney tunes") {
          return title.includes("bugs bunny") || title.includes("merrie melodies") || title.includes("looney");
        }
        return title.includes(filter);
      })
    : unfilteredVideos;

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

        {/* Library view: search + results (or all videos when no search) */}
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

            {stats?.categories && stats.categories.length > 0 && (
              <FilterBar
                categories={stats.categories}
                activeFilter={activeFilter}
                onFilterChange={setActiveFilter}
                totalResults={unfilteredVideos?.length}
              />
            )}

            <VideoGrid
              results={displayedVideos}
              isLoading={isLoading}
              searchTime={hasSearched ? searchResult?.search_time_ms : undefined}
              query={hasSearched ? searchResult?.query : undefined}
              onPlay={handlePlay}
              onFindSimilar={handleFindSimilar}
            />
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
