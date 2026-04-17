import { useState, useRef, useEffect } from "react";
import { X, SkipForward, SkipBack, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { getSegmentPlayUrl, formatDuration } from "@/lib/api";
import type { VideoResult } from "@/types";

interface HighlightReelProps {
  videos: VideoResult[];
  query: string;
  onClose: () => void;
}

interface ReelSegment {
  video: VideoResult;
  segmentIndex: number;
  startSeconds: number;
  endSeconds: number;
  relevancePct: number;
}

export function HighlightReel({ videos, query, onClose }: HighlightReelProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showTitle, setShowTitle] = useState(true);

  // Build the reel: best segment from each video, sorted by relevance
  const reel: ReelSegment[] = videos
    .filter((v) => v.top_segments.length > 0)
    .map((v) => {
      const best = v.top_segments[0];
      return {
        video: v,
        segmentIndex: best.segment_index,
        startSeconds: best.start_seconds ?? best.segment_index * 120,
        endSeconds: best.end_seconds ?? (best.segment_index + 1) * 120,
        relevancePct: v.relevance_pct,
      };
    })
    .slice(0, 8); // Top 8

  const current = reel[currentIndex];

  // Show title card for 2 seconds, then start playing
  useEffect(() => {
    setShowTitle(true);
    const timer = setTimeout(() => setShowTitle(false), 2000);
    return () => clearTimeout(timer);
  }, [currentIndex]);

  // Auto-advance when segment file ends
  useEffect(() => {
    if (!current || showTitle) return;
    const video = videoRef.current;
    if (!video) return;

    const handleEnded = () => {
      if (currentIndex < reel.length - 1) {
        setCurrentIndex((i) => i + 1);
      }
    };
    video.addEventListener("ended", handleEnded);

    return () => video.removeEventListener("ended", handleEnded);
  }, [current, currentIndex, reel.length, showTitle]);

  if (reel.length === 0) return null;

  const totalDuration = reel.reduce((sum, s) => sum + (s.endSeconds - s.startSeconds), 0);

  return (
    <div className="fixed inset-0 z-50 bg-black flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 bg-black/80 backdrop-blur z-10">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-primary">
            <Sparkles className="w-4 h-4" />
            <span className="text-sm font-medium text-white">Highlight Reel</span>
          </div>
          <span className="text-xs text-white/50">
            &ldquo;{query}&rdquo; &middot; {reel.length} clips &middot; ~{formatDuration(totalDuration)}
          </span>
        </div>
        <Button variant="ghost" size="sm" className="text-white hover:bg-white/10" onClick={onClose}>
          <X className="w-4 h-4" />
        </Button>
      </div>

      {/* Video area */}
      <div className="flex-1 flex items-center justify-center relative">
        {showTitle ? (
          // Title card
          <div className="text-center animate-in fade-in duration-500 space-y-3">
            <Badge variant="secondary" className="text-xs">
              {currentIndex + 1} of {reel.length}
            </Badge>
            <h2 className="text-3xl font-bold text-white">
              {current.video.title}
            </h2>
            <p className="text-white/50 text-sm">
              {current.video.year}
              {current.relevancePct > 0 && ` · ${current.relevancePct}% match`}
            </p>
            <p className="text-white/30 text-xs">
              Segment {formatDuration(current.startSeconds)}–{formatDuration(current.endSeconds)}
            </p>
          </div>
        ) : (
          // Video player
          <video
            ref={videoRef}
            key={`${current.video.video_id}-${currentIndex}`}
            className="max-h-full max-w-full"
            controls
            autoPlay
          >
            <source src={getSegmentPlayUrl(current.video.video_id, current.segmentIndex)} type="video/mp4" />
          </video>
        )}

        {/* Video title overlay (bottom) */}
        {!showTitle && (
          <div className="absolute bottom-16 left-0 right-0 text-center pointer-events-none">
            <span className="bg-black/60 text-white text-sm px-3 py-1.5 rounded-full backdrop-blur-sm">
              {current.video.title} · {formatDuration(current.startSeconds)}–{formatDuration(current.endSeconds)}
            </span>
          </div>
        )}
      </div>

      {/* Controls + progress */}
      <div className="px-6 py-4 bg-black/80 backdrop-blur space-y-3">
        {/* Segment progress dots */}
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="text-white hover:bg-white/10"
            disabled={currentIndex === 0}
            onClick={() => setCurrentIndex((i) => i - 1)}
          >
            <SkipBack className="w-4 h-4" />
          </Button>

          <div className="flex gap-1.5">
            {reel.map((seg, i) => (
              <button
                key={i}
                type="button"
                className={`transition-all duration-200 rounded-full ${
                  i === currentIndex
                    ? "w-8 h-2 bg-primary"
                    : i < currentIndex
                      ? "w-2 h-2 bg-white/50"
                      : "w-2 h-2 bg-white/20"
                }`}
                onClick={() => setCurrentIndex(i)}
                title={seg.video.title}
              />
            ))}
          </div>

          <Button
            variant="ghost"
            size="sm"
            className="text-white hover:bg-white/10"
            disabled={currentIndex === reel.length - 1}
            onClick={() => setCurrentIndex((i) => i + 1)}
          >
            <SkipForward className="w-4 h-4" />
          </Button>
        </div>

        {/* Clip list */}
        <div className="flex gap-2 overflow-x-auto pb-1">
          {reel.map((seg, i) => (
            <button
              key={i}
              type="button"
              className={`flex-shrink-0 rounded-lg overflow-hidden border-2 transition-all ${
                i === currentIndex
                  ? "border-primary"
                  : "border-transparent opacity-60 hover:opacity-100"
              }`}
              onClick={() => setCurrentIndex(i)}
            >
              <div className="w-28 h-16 bg-muted relative">
                <img
                  src={seg.video.thumbnail_url}
                  alt={seg.video.title}
                  className="w-full h-full object-cover"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                />
                <span className="absolute bottom-0.5 right-0.5 bg-black/70 text-white text-[9px] px-1 rounded">
                  {formatDuration(seg.endSeconds - seg.startSeconds)}
                </span>
              </div>
              <p className="text-[10px] text-white/70 px-1 py-0.5 truncate w-28 bg-black/50">
                {seg.video.title}
              </p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
