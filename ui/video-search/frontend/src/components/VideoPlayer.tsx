import { useRef, useState, useEffect } from "react";
import { X, Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { formatDuration, getFullVideoUrl } from "@/lib/api";
import type { VideoSegment } from "@/types";

interface VideoPlayerProps {
  videoId: string;
  title: string;
  segments: VideoSegment[];
  totalDuration?: number | null;
  initialSeek?: number;
  onClose: () => void;
}

export function VideoPlayer({
  videoId,
  title,
  segments,
  totalDuration,
  initialSeek,
  onClose,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentTime, setCurrentTime] = useState(0);

  const videoUrl = getFullVideoUrl(videoId);
  const duration = totalDuration || 600;

  // Deduplicate segments by segment_index, keep best distance
  const uniqueSegments = new Map<number, VideoSegment>();
  for (const seg of segments) {
    const existing = uniqueSegments.get(seg.segment_index);
    if (!existing || seg.distance < existing.distance) {
      uniqueSegments.set(seg.segment_index, seg);
    }
  }
  const dedupedSegments = [...uniqueSegments.values()].sort(
    (a, b) => a.distance - b.distance
  );

  // Distance range for color mapping
  const bestDistance = dedupedSegments[0]?.distance ?? 0;
  const worstDistance = dedupedSegments[dedupedSegments.length - 1]?.distance ?? 1;
  const distanceRange = worstDistance - bestDistance || 1;

  // Build relevance map
  const relevanceMap = new Map<number, number>();
  for (const seg of dedupedSegments) {
    relevanceMap.set(seg.segment_index, seg.distance);
  }

  // All segment slots for the timeline
  const totalSegments = Math.ceil(duration / 120);
  const allSlots = Array.from({ length: totalSegments }, (_, i) => i);

  function getRelevancePercent(distance: number): number {
    return Math.round((1 - distance / 2) * 100);
  }

  function getSegmentOpacity(segIndex: number): number {
    const dist = relevanceMap.get(segIndex);
    if (dist === undefined) return 0.08;
    const normalized = (dist - bestDistance) / distanceRange;
    return 1.0 - normalized * 0.7;
  }

  function seekTo(seconds: number) {
    if (videoRef.current) {
      videoRef.current.currentTime = seconds;
      videoRef.current.play();
    }
  }

  // Seek to initial position when video loads
  useEffect(() => {
    if (initialSeek && videoRef.current) {
      const handleCanPlay = () => {
        videoRef.current!.currentTime = initialSeek;
      };
      videoRef.current.addEventListener("canplay", handleCanPlay, { once: true });
      return () => videoRef.current?.removeEventListener("canplay", handleCanPlay);
    }
  }, [initialSeek]);

  // Track current time
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const handler = () => setCurrentTime(video.currentTime);
    video.addEventListener("timeupdate", handler);
    return () => video.removeEventListener("timeupdate", handler);
  }, []);

  // Which segment is currently playing
  const currentSegmentIndex = Math.floor(currentTime / 120);

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border flex-shrink-0">
          <div>
            <h2 className="text-lg font-medium text-foreground truncate">
              {title}
            </h2>
            <p className="text-xs text-muted-foreground">
              {formatDuration(duration)} total
              {dedupedSegments.length > 0 && ` · ${dedupedSegments.length} matching segments`}
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Video — full raw video */}
        <div className="aspect-video bg-black flex-shrink-0">
          <video
            ref={videoRef}
            controls
            autoPlay
            className="w-full h-full"
          >
            <source src={videoUrl} type="video/mp4" />
          </video>
        </div>

        {/* Timeline + segments */}
        {segments.length > 0 && (
          <div className="px-4 pt-4 pb-2 flex-shrink-0">
            <div className="flex items-center justify-between mb-1.5">
              <p className="text-xs text-muted-foreground uppercase tracking-wider">
                Match timeline
              </p>
              <p className="text-xs text-muted-foreground">
                {formatDuration(0)} — {formatDuration(duration)}
              </p>
            </div>

            {/* Timeline bar */}
            <div className="relative flex gap-0.5 h-8 rounded overflow-hidden bg-muted">
              {allSlots.map((segIndex) => {
                const isMatched = relevanceMap.has(segIndex);
                const isCurrent = segIndex === currentSegmentIndex;
                const opacity = getSegmentOpacity(segIndex);
                const segStart = segIndex * 120;
                const segEnd = Math.min((segIndex + 1) * 120, duration);
                const widthPct = ((segEnd - segStart) / duration) * 100;

                return (
                  <button
                    key={segIndex}
                    type="button"
                    className={`relative transition-all duration-200 ${
                      isCurrent
                        ? "ring-2 ring-primary ring-offset-1 ring-offset-card"
                        : "hover:brightness-110"
                    } ${isMatched ? "cursor-pointer" : "cursor-default"}`}
                    style={{
                      width: `${widthPct}%`,
                      backgroundColor: isMatched
                        ? `hsl(221.2 83.2% 53.3% / ${opacity})`
                        : undefined,
                    }}
                    onClick={() => seekTo(segStart)}
                    title={`${formatDuration(segStart)}–${formatDuration(segEnd)}${
                      isMatched
                        ? ` (${getRelevancePercent(relevanceMap.get(segIndex)!)}% match)`
                        : ""
                    }`}
                  />
                );
              })}

              {/* Playhead indicator */}
              <div
                className="absolute top-0 h-full w-0.5 bg-foreground/80 pointer-events-none transition-all duration-200"
                style={{ left: `${(currentTime / duration) * 100}%` }}
              />
            </div>
            <p className="text-[10px] text-muted-foreground mt-1">
              Darker = stronger match · Click any segment to jump
            </p>
          </div>
        )}

        {/* Segment list */}
        {dedupedSegments.length > 0 && (
          <div className="px-4 pb-4 overflow-y-auto flex-shrink">
            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-2">
              Matching segments — best match first
            </p>
            <div className="space-y-1">
              {dedupedSegments.map((seg, i) => {
                const relevance = getRelevancePercent(seg.distance);
                const isCurrent = seg.segment_index === currentSegmentIndex;
                const segStart = seg.start_seconds ?? seg.segment_index * 120;
                const segEnd = seg.end_seconds ?? (seg.segment_index + 1) * 120;

                return (
                  <button
                    key={seg.segment_index}
                    type="button"
                    className={`w-full flex items-center gap-3 p-2 rounded-md text-left transition-colors duration-200 ${
                      isCurrent
                        ? "bg-primary/10 border border-primary/20"
                        : "hover:bg-muted border border-transparent"
                    }`}
                    onClick={() => seekTo(segStart)}
                  >
                    {i === 0 && <Star className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />}
                    {i > 0 && <div className="w-3.5 flex-shrink-0" />}

                    <span className="text-sm text-foreground min-w-[100px]">
                      {formatDuration(segStart)}–{formatDuration(segEnd)}
                    </span>

                    {i === 0 && (
                      <span className="text-[10px] bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded">
                        Best match
                      </span>
                    )}

                    <div className="flex-1" />

                    <div className="flex items-center gap-2 flex-shrink-0">
                      <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${relevance}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground w-8 text-right">
                        {relevance}%
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
