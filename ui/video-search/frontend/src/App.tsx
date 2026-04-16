import { useState, useCallback, useEffect } from "react";
import { Header } from "@/components/Header";
import { SearchBar } from "@/components/SearchBar";
import { VideoGrid } from "@/components/VideoGrid";
import { VideoPlayer } from "@/components/VideoPlayer";
import { LibraryStats } from "@/components/LibraryStats";
import { AddVideos } from "@/components/AddVideos";
import { Button } from "@/components/ui/button";
import { Search, LayoutGrid, Plus } from "lucide-react";
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

type View = "search" | "browse" | "add";

export default function App() {
  const [view, setView] = useState<View>("search");
  const [searchResult, setSearchResult] = useState<SearchResponse | null>(null);
  const [browseVideos, setBrowseVideos] = useState<VideoResult[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<StatsType | null>(null);
  const [searchLabel, setSearchLabel] = useState<string | undefined>();
  const [externalQuery, setExternalQuery] = useState<string | undefined>();

  // Player state
  const [playerVideo, setPlayerVideo] = useState<VideoResult | null>(null);
  const [playerUrl, setPlayerUrl] = useState<string | null>(null);
  const [activeSegment, setActiveSegment] = useState(0);

  // Load stats on mount
  useEffect(() => {
    getLibraryStats().then(setStats).catch(() => {});
  }, []);

  const handleSearch = useCallback(async (query: string) => {
    setView("search");
    setIsLoading(true);
    setError(null);
    setSearchLabel(undefined);
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

  const handleBrowse = useCallback(async () => {
    setView("browse");
    setIsLoading(true);
    setError(null);
    try {
      const { videos } = await listVideos();
      // Convert VideoListItem to VideoResult shape for the grid
      setBrowseVideos(
        videos.map((v) => ({
          ...v,
          best_distance: 0,
          relevance_pct: 0,
          matching_intervals: 0,
          top_segments: [],
        }))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load library");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleFindSimilar = useCallback(async (videoId: string) => {
    setView("search");
    setIsLoading(true);
    setError(null);
    setSearchLabel(`Videos similar to "${videoId}"`);
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
  }, []);

  const handlePlay = useCallback(
    (videoId: string, segmentIndex: number) => {
      const allResults =
        view === "browse" ? browseVideos : searchResult?.results;
      const video = allResults?.find((v) => v.video_id === videoId);
      if (!video) return;

      setPlayerVideo(video);
      setPlayerUrl(getSegmentPlayUrl(videoId, segmentIndex));
      setActiveSegment(segmentIndex);
    },
    [view, browseVideos, searchResult]
  );

  const handleSegmentChange = useCallback(
    (segmentIndex: number) => {
      if (!playerVideo) return;
      setPlayerUrl(getSegmentPlayUrl(playerVideo.video_id, segmentIndex));
      setActiveSegment(segmentIndex);
    },
    [playerVideo]
  );

  const currentResults =
    view === "browse" ? browseVideos : searchResult?.results ?? null;

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <Header />

      <main className="flex-1 w-full max-w-7xl mx-auto p-4 md:p-6 lg:p-8 space-y-6">
        {/* Stats */}
        <LibraryStats stats={stats} />

        {/* View tabs */}
        <div className="flex items-center gap-2 border-b border-border pb-2">
          <Button
            variant={view === "search" ? "default" : "ghost"}
            size="sm"
            className="gap-1.5"
            onClick={() => setView("search")}
          >
            <Search className="w-4 h-4" />
            Search
          </Button>
          <Button
            variant={view === "browse" ? "default" : "ghost"}
            size="sm"
            className="gap-1.5"
            onClick={handleBrowse}
          >
            <LayoutGrid className="w-4 h-4" />
            Browse library
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

        {/* Search view */}
        {view === "search" && (
          <div className="space-y-6">
            <SearchBar onSearch={handleSearch} isLoading={isLoading} externalQuery={externalQuery} />

            {searchLabel && !isLoading && (
              <p className="text-sm font-medium text-foreground">
                {searchLabel}
              </p>
            )}
          </div>
        )}

        {/* Add videos view */}
        {view === "add" && <AddVideos />}

        {error && (
          <div className="bg-destructive/10 border border-destructive/20 text-destructive rounded-lg p-4 text-sm">
            {error}
          </div>
        )}

        {view !== "add" && (
          <VideoGrid
            results={currentResults}
            isLoading={isLoading}
            searchTime={
              view === "search" ? searchResult?.search_time_ms : undefined
            }
            query={view === "search" ? searchResult?.query : undefined}
            onPlay={handlePlay}
            onFindSimilar={handleFindSimilar}
          />
        )}
      </main>

      {playerVideo && playerUrl && (
        <VideoPlayer
          videoId={playerVideo.video_id}
          title={playerVideo.title}
          videoUrl={playerUrl}
          segments={playerVideo.top_segments}
          activeSegment={activeSegment}
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
