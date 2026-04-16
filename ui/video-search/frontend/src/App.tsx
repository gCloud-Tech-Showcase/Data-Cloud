import { useState, useCallback } from "react";
import { Header } from "@/components/Header";
import { SearchBar } from "@/components/SearchBar";
import { VideoGrid } from "@/components/VideoGrid";
import { VideoPlayer } from "@/components/VideoPlayer";
import { searchVideos, getSegmentPlayUrl } from "@/lib/api";
import type { VideoResult, SearchResponse } from "@/types";

export default function App() {
  const [searchResult, setSearchResult] = useState<SearchResponse | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Player state
  const [playerVideo, setPlayerVideo] = useState<VideoResult | null>(null);
  const [playerUrl, setPlayerUrl] = useState<string | null>(null);
  const [activeSegment, setActiveSegment] = useState(0);

  const handleSearch = useCallback(async (query: string) => {
    setIsSearching(true);
    setError(null);
    try {
      const result = await searchVideos(query);
      setSearchResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setSearchResult(null);
    } finally {
      setIsSearching(false);
    }
  }, []);

  const handlePlay = useCallback(
    (videoId: string, segmentIndex: number) => {
      const video = searchResult?.results.find((v) => v.video_id === videoId);
      if (!video) return;

      setPlayerVideo(video);
      setPlayerUrl(getSegmentPlayUrl(videoId, segmentIndex));
      setActiveSegment(segmentIndex);
    },
    [searchResult]
  );

  const handleSegmentChange = useCallback(
    (segmentIndex: number) => {
      if (!playerVideo) return;
      setPlayerUrl(getSegmentPlayUrl(playerVideo.video_id, segmentIndex));
      setActiveSegment(segmentIndex);
    },
    [playerVideo]
  );

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <Header />

      <main className="flex-1 w-full max-w-7xl mx-auto p-4 md:p-6 lg:p-8 space-y-8">
        <div className="pt-8 pb-4">
          <h2 className="text-3xl font-bold tracking-tight text-foreground text-center mb-2">
            Find any video by describing it
          </h2>
          <p className="text-sm text-muted-foreground text-center mb-8">
            Powered by BigQuery Vector Search and Gemini multimodal embeddings
          </p>
          <SearchBar onSearch={handleSearch} isLoading={isSearching} />
        </div>

        {error && (
          <div className="bg-destructive/10 border border-destructive/20 text-destructive rounded-lg p-4 text-sm">
            {error}
          </div>
        )}

        <VideoGrid
          results={searchResult?.results ?? null}
          isLoading={isSearching}
          searchTime={searchResult?.search_time_ms}
          query={searchResult?.query}
          onPlay={handlePlay}
        />
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
