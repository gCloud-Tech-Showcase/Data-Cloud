import { X, Clock, Play, Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatDuration } from "@/lib/api";
import type { VideoSegment } from "@/types";

interface VideoPlayerProps {
  videoId: string;
  title: string;
  videoUrl: string;
  segments: VideoSegment[];
  activeSegment: number;
  totalDuration?: number | null;
  onSegmentChange: (segmentIndex: number) => void;
  onClose: () => void;
}

export function VideoPlayer({
  title,
  videoUrl,
  segments,
  activeSegment,
  totalDuration,
  onSegmentChange,
  onClose,
}: VideoPlayerProps) {
  // Sort segments by relevance for the list
  const sortedByRelevance = [...segments].sort((a, b) => a.distance - b.distance);
  const bestDistance = sortedByRelevance[0]?.distance ?? 0;
  const worstDistance = sortedByRelevance[sortedByRelevance.length - 1]?.distance ?? 1;
  const distanceRange = worstDistance - bestDistance || 1;

  // Deduplicate segments by segment_index for the timeline
  const uniqueSegments = new Map<number, VideoSegment>();
  for (const seg of segments) {
    const existing = uniqueSegments.get(seg.segment_index);
    if (!existing || seg.distance < existing.distance) {
      uniqueSegments.set(seg.segment_index, seg);
    }
  }

  // Compute total duration for the timeline
  const duration = totalDuration || Math.max(...segments.map((s) => s.end_seconds), 120);

  // Get all unique segment indices that exist in the video
  const maxSegmentIndex = Math.max(...segments.map((s) => s.segment_index));
  const allSegmentSlots = Array.from({ length: maxSegmentIndex + 1 }, (_, i) => i);

  // Build relevance map: segment_index → best distance
  const relevanceMap = new Map<number, number>();
  for (const seg of segments) {
    const existing = relevanceMap.get(seg.segment_index);
    if (existing === undefined || seg.distance < existing) {
      relevanceMap.set(seg.segment_index, seg.distance);
    }
  }

  function getSegmentOpacity(segIndex: number): number {
    const dist = relevanceMap.get(segIndex);
    if (dist === undefined) return 0.1; // unmatched segment
    // Map distance to opacity: best match = 1.0, worst = 0.3
    const normalized = (dist - bestDistance) / distanceRange;
    return 1.0 - normalized * 0.7;
  }

  function getRelevancePercent(distance: number): number {
    return Math.round((1 - distance / 2) * 100);
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border flex-shrink-0">
          <h2 className="text-lg font-medium text-foreground truncate">
            {title}
          </h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Video */}
        <div className="aspect-video bg-black flex-shrink-0">
          <video
            key={videoUrl}
            controls
            autoPlay
            className="w-full h-full"
          >
            <source src={videoUrl} type="video/mp4" />
          </video>
        </div>

        {/* Timeline visualization */}
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
            <div className="flex gap-0.5 h-8 rounded overflow-hidden bg-muted">
              {allSegmentSlots.map((segIndex) => {
                const isMatched = relevanceMap.has(segIndex);
                const isActive = segIndex === activeSegment;
                const opacity = getSegmentOpacity(segIndex);
                const segStart = segIndex * 120;
                const segEnd = Math.min((segIndex + 1) * 120, duration);
                const widthPct = ((segEnd - segStart) / duration) * 100;

                return (
                  <button
                    key={segIndex}
                    type="button"
                    className={`relative transition-all duration-200 ${
                      isActive
                        ? "ring-2 ring-primary ring-offset-1 ring-offset-card"
                        : "hover:brightness-110"
                    } ${isMatched ? "cursor-pointer" : "cursor-default"}`}
                    style={{
                      width: `${widthPct}%`,
                      backgroundColor: isMatched
                        ? `hsl(221.2 83.2% 53.3% / ${opacity})`
                        : undefined,
                    }}
                    onClick={() => isMatched && onSegmentChange(segIndex)}
                    title={`${formatDuration(segStart)}–${formatDuration(segEnd)}${
                      isMatched
                        ? ` (${getRelevancePercent(relevanceMap.get(segIndex)!)}% match)`
                        : " (no match)"
                    }`}
                  >
                    {isActive && (
                      <div className="absolute inset-0 flex items-center justify-center">
                        <Play className="w-3 h-3 text-white drop-shadow" />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
            <div className="flex justify-between mt-1">
              <span className="text-[10px] text-muted-foreground">Darker = stronger match</span>
              <button
                type="button"
                className="text-[10px] text-primary hover:underline"
                onClick={() => onSegmentChange(0)}
              >
                Watch from start
              </button>
            </div>
          </div>
        )}

        {/* Segment list sorted by relevance */}
        {sortedByRelevance.length > 1 && (
          <div className="px-4 pb-4 overflow-y-auto flex-shrink">
            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-2">
              Matching segments — best match first
            </p>
            <div className="space-y-1.5">
              {/* Deduplicate by segment_index for the list */}
              {[...uniqueSegments.values()]
                .sort((a, b) => a.distance - b.distance)
                .map((seg, i) => {
                  const relevance = getRelevancePercent(seg.distance);
                  const isActive = seg.segment_index === activeSegment;

                  return (
                    <button
                      key={seg.segment_index}
                      type="button"
                      className={`w-full flex items-center gap-3 p-2 rounded-md text-left transition-colors duration-200 ${
                        isActive
                          ? "bg-primary/10 border border-primary/20"
                          : "hover:bg-muted border border-transparent"
                      }`}
                      onClick={() => onSegmentChange(seg.segment_index)}
                    >
                      {i === 0 && (
                        <Star className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
                      )}
                      {i > 0 && <div className="w-3.5 flex-shrink-0" />}

                      <Clock className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                      <span className="text-sm text-foreground">
                        {formatDuration(seg.start_seconds)}–{formatDuration(seg.end_seconds)}
                      </span>

                      {i === 0 && (
                        <Badge variant="secondary" className="text-[10px] py-0">
                          Best match
                        </Badge>
                      )}

                      <div className="flex-1" />

                      {/* Relevance bar */}
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary rounded-full transition-all"
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
