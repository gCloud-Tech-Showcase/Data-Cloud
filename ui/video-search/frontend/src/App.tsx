import { useState, useCallback, useEffect, useMemo } from "react";
import { Header } from "@/components/Header";
import { SearchBar } from "@/components/SearchBar";
import { VideoGrid } from "@/components/VideoGrid";
import { VideoPlayer } from "@/components/VideoPlayer";
import { LibraryStats } from "@/components/LibraryStats";
import { AddVideos } from "@/components/AddVideos";
import { FilterSidebar } from "@/components/FilterSidebar";
import { ResultsBar } from "@/components/ResultsBar";
import { SelectionBar } from "@/components/SelectionBar";
import { VideoDetailPanel } from "@/components/VideoDetailPanel";
import { HighlightReel } from "@/components/HighlightReel";
import { Footer } from "@/components/Footer";
import { ChatPanel } from "@/components/ChatPanel";
import { ArrowLeft } from "lucide-react";
import {
  searchVideos,
  getLibraryStats,
  listVideos,
  findSimilar,
} from "@/lib/api";
import type {
  VideoResult,
  SearchResponse,
  LibraryStats as StatsType,
  AgentAction,
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

  // Selection state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [autoExportName, setAutoExportName] = useState<string | undefined>();

  // Detail panel state
  const [detailVideoId, setDetailVideoId] = useState<string | null>(null);
  const [showHighlightReel, setShowHighlightReel] = useState(false);

  // Player state
  const [playerVideo, setPlayerVideo] = useState<VideoResult | null>(null);
  const [activeSegment, setActiveSegment] = useState(0);

  // Load initial state from URL params
  useEffect(() => {
    getLibraryStats().then(setStats).catch(() => {}).finally(() => setStatsLoading(false));
    loadAllVideos();

    const params = new URLSearchParams(window.location.search);
    const q = params.get("q");
    if (q) {
      setExternalQuery(q);
      // Delay search to let stats/videos load first
      setTimeout(() => handleSearch(q), 500);
    }

    // Restore filters from URL
    const filterFields = ["category", "mood", "color_mode", "style"];
    const restoredFilters: Record<string, Set<string>> = {};
    for (const field of filterFields) {
      const values = params.getAll(field);
      if (values.length > 0) {
        restoredFilters[field] = new Set(values);
      }
    }
    if (Object.keys(restoredFilters).length > 0) {
      setActiveFilters(restoredFilters);
    }
  }, []);

  // Sync URL with search state
  useEffect(() => {
    const params = new URLSearchParams();
    if (hasSearched && searchResult?.query && !searchResult.query.startsWith("similar:")) {
      params.set("q", searchResult.query);
    }
    for (const [field, values] of Object.entries(activeFilters)) {
      for (const value of values) {
        params.append(field, value);
      }
    }
    const search = params.toString();
    const url = search ? `${window.location.pathname}?${search}` : window.location.pathname;
    window.history.replaceState(null, "", url);
  }, [hasSearched, searchResult, activeFilters]);

  // Global keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Escape: close modals/panels in order
      if (e.key === "Escape") {
        if (showHighlightReel) {
          setShowHighlightReel(false);
        } else if (playerVideo) {
          setPlayerVideo(null);
        } else if (detailVideoId) {
          setDetailVideoId(null);
        } else if (view === "add") {
          setView("library");
        }
      }
      // Ctrl/Cmd+K: focus search
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        const searchInput = document.querySelector<HTMLInputElement>('input[placeholder*="Search"]');
        searchInput?.focus();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [playerVideo, detailVideoId, showHighlightReel, view]);

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
          content_warnings: v.content_warnings ?? null,
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
      setActiveSegment(segmentIndex);
    },
    [hasSearched, allVideos, searchResult]
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

  const handleToggleSelect = useCallback((videoId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(videoId)) next.delete(videoId);
      else next.add(videoId);
      return next;
    });
  }, []);

  const handleClearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  // Agent action dispatcher — discriminated union provides type narrowing
  const handleAgentAction = useCallback(
    (action: AgentAction) => {
      switch (action.type) {
        case "search":
          setExternalQuery(action.query);
          handleSearch(action.query);
          break;
        case "apply_filter":
          handleFilterChange(action.field, action.value);
          break;
        case "clear_filters":
          handleClearAllFilters();
          break;
        case "play":
          handlePlay(action.video_id, 0);
          break;
        case "show_details":
          setDetailVideoId(action.video_id);
          break;
        case "find_similar":
          handleFindSimilar(action.video_id);
          break;
        case "create_collection":
          setSelectedIds(new Set(action.video_ids));
          setAutoExportName(action.name);
          break;
      }
    },
    [handleSearch, handleFilterChange, handleClearAllFilters, handlePlay, handleFindSimilar]
  );

  // Unfiltered results (memoized to provide stable reference for downstream useMemo)
  const unfilteredVideos = useMemo(() => {
    if (hasSearched) return searchResult?.results ?? null;
    return allVideos.length > 0 ? allVideos : null;
  }, [hasSearched, searchResult?.results, allVideos]);

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

  // Contextual filter counts: computed from current results, not the full library
  const contextualFilters = useMemo(() => {
    if (!stats?.filters) return null;
    if (!unfilteredVideos) return stats.filters;

    const fields = ["category", "mood", "color_mode", "style", "content_warnings"] as const;
    const result: Record<string, { name: string; count: number }[]> = {};

    for (const field of fields) {
      const counts = new Map<string, number>();
      for (const video of unfilteredVideos) {
        const value = (video as unknown as Record<string, unknown>)[field];
        if (typeof value === "string" && value) {
          counts.set(value, (counts.get(value) || 0) + 1);
        }
      }
      result[field] = [...counts.entries()]
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count);
    }

    return result;
  }, [stats?.filters, unfilteredVideos]);

  const hasFilters = contextualFilters && Object.values(contextualFilters).some((f) => f.length > 0);
  const hasActiveFilters = Object.values(activeFilters).some((s) => s.size > 0);

  // Memoize selected videos for SelectionBar
  const selectedVideos = useMemo(() => {
    if (selectedIds.size === 0) return [];
    const source = displayedVideos ?? allVideos;
    return [...selectedIds]
      .map((id) => source.find((v) => v.video_id === id))
      .filter(Boolean) as VideoResult[];
  }, [selectedIds, displayedVideos, allVideos]);

  return (
    <div className="min-h-screen bg-muted/40 text-foreground flex flex-col">
      <Header
        onAddVideos={() => setView("add")}
        isAddView={view === "add"}
        onBackToLibrary={() => setView("library")}
      />

      <main className="flex-1 w-full max-w-7xl mx-auto p-4 md:p-6 lg:p-8 space-y-6">
        {view === "library" && (
          <>
          <LibraryStats stats={stats} isLoading={statsLoading} />
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

            <div className="lg:flex lg:gap-6 space-y-4 lg:space-y-0">
              {hasFilters && contextualFilters && (
                <FilterSidebar
                  filters={contextualFilters}
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
                    hasSearchResults={hasSearched && (searchResult?.results?.length ?? 0) > 0}
                    onHighlightReel={() => setShowHighlightReel(true)}
                  />
                )}

                <VideoGrid
                  results={displayedVideos}
                  isLoading={isLoading}
                  onPlay={handlePlay}
                  onFindSimilar={handleFindSimilar}
                  onClearFilters={hasActiveFilters ? handleClearAllFilters : undefined}
                  onShowDetails={(id) => setDetailVideoId(id)}
                  selectedIds={selectedIds}
                  onToggleSelect={handleToggleSelect}
                />
              </div>
            </div>
          </div>
          </>
        )}

        {view === "add" && (
          <div className="space-y-4">
            <button
              type="button"
              className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => setView("library")}
            >
              <ArrowLeft className="w-4 h-4" />
              Back to library
            </button>
            <AddVideos />
          </div>
        )}
      </main>

      <SelectionBar
        selectedVideos={selectedVideos}
        onClearSelection={handleClearSelection}
        autoExportName={autoExportName}
        onAutoExportHandled={() => setAutoExportName(undefined)}
      />

      <Footer />

      {showHighlightReel && searchResult && (
        <HighlightReel
          videos={searchResult.results}
          query={searchResult.query}
          onClose={() => setShowHighlightReel(false)}
        />
      )}

      {detailVideoId && (
        <VideoDetailPanel
          videoId={detailVideoId}
          onClose={() => setDetailVideoId(null)}
          onPlay={(id) => {
            setDetailVideoId(null);
            const video = (displayedVideos ?? allVideos).find((v) => v.video_id === id);
            if (video) {
              setPlayerVideo(video);
              setActiveSegment(0);
            }
          }}
          onFindSimilar={(id) => {
            setDetailVideoId(null);
            handleFindSimilar(id);
          }}
        />
      )}

      {playerVideo && (
        <VideoPlayer
          videoId={playerVideo.video_id}
          title={playerVideo.title}
          segments={playerVideo.top_segments}
          totalDuration={playerVideo.duration_total_seconds}
          initialSeek={activeSegment * 120}
          onClose={() => setPlayerVideo(null)}
        />
      )}

      <ChatPanel onAction={handleAgentAction} />
    </div>
  );
}
