import { Play, ExternalLink, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { VideoResult } from "@/types";
import { formatDuration } from "@/lib/api";

interface VideoCardProps {
  video: VideoResult;
  onPlay: (videoId: string, segmentIndex: number) => void;
  onFindSimilar?: (videoId: string) => void;
  isSelected?: boolean;
  onToggleSelect?: (videoId: string) => void;
}

export function VideoCard({ video, onPlay, onFindSimilar, isSelected, onToggleSelect }: VideoCardProps) {
  const bestSegment = video.top_segments[0] || { segment_index: 0, start_seconds: 0, end_seconds: 120, distance: 0 };

  return (
    <Card className={`overflow-hidden group shadow-sm hover:shadow-lg transition-all duration-200 bg-background flex flex-col ${isSelected ? "ring-2 ring-primary" : ""}`}>
      {/* Thumbnail — 16:9 aspect ratio */}
      <div
        className="relative aspect-video bg-muted cursor-pointer flex-shrink-0"
        onClick={() => onPlay(video.video_id, bestSegment.segment_index)}
      >
        <img
          src={video.thumbnail_url}
          alt={video.title}
          className="w-full h-full object-cover"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />

        {/* Hover overlay with play button */}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors duration-200 flex items-center justify-center">
          <Play className="w-12 h-12 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-200 drop-shadow-lg" />
        </div>

        {/* Selection checkbox — top left */}
        {onToggleSelect && (
          <button
            type="button"
            className={`absolute top-2 left-2 z-10 w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
              isSelected
                ? "bg-primary border-primary text-primary-foreground"
                : "border-white/70 bg-black/30 opacity-0 group-hover:opacity-100"
            }`}
            onClick={(e) => {
              e.stopPropagation();
              onToggleSelect(video.video_id);
            }}
          >
            {isSelected && (
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            )}
          </button>
        )}

        {/* Category badge */}
        {video.category && (
          <span className={`absolute ${onToggleSelect ? "top-2 left-9" : "top-2 left-2"} bg-black/60 text-white text-[10px] px-1.5 py-0.5 rounded capitalize backdrop-blur-sm`}>
            {video.category}
          </span>
        )}

        {/* Match badge — top right, only when searching */}
        {video.relevance_pct > 0 && (
          <Badge
            variant="secondary"
            className="absolute top-2 right-2 bg-background/80 backdrop-blur-sm"
          >
            {video.relevance_pct}% match
          </Badge>
        )}

        {/* Duration badge — bottom right */}
        {video.duration_total_seconds && (
          <span className="absolute bottom-2 right-2 bg-black/70 text-white text-xs px-1.5 py-0.5 rounded">
            {formatDuration(video.duration_total_seconds)}
          </span>
        )}
      </div>

      {/* Content — always visible */}
      <CardContent className="p-3 flex flex-col flex-1 justify-between gap-2">
        <div className="space-y-1">
          <h3 className="text-sm font-medium text-foreground line-clamp-1">
            {video.title}
          </h3>
          {video.year && (
            <p className="text-xs text-muted-foreground">{video.year}</p>
          )}
          {video.ai_description && (
            <p className="text-xs text-muted-foreground/80 line-clamp-2 leading-relaxed">
              {video.ai_description}
            </p>
          )}

          {/* Match info — only when searching */}
          {video.matching_intervals > 0 && (
            <p className="text-[11px] text-primary/70">
              Best match at {formatDuration(bestSegment.start_seconds)}–{formatDuration(bestSegment.end_seconds)}
            </p>
          )}
        </div>

        {/* Actions — always visible, enhanced on hover */}
        <div className="flex gap-1.5 pt-1">
          <Button
            size="sm"
            variant="ghost"
            className="h-7 text-xs gap-1 text-muted-foreground group-hover:bg-primary group-hover:text-primary-foreground transition-colors"
            onClick={(e) => {
              e.stopPropagation();
              onPlay(video.video_id, bestSegment.segment_index);
            }}
          >
            <Play className="w-3 h-3" />
            Play
          </Button>
          {onFindSimilar && (
            <Button
              size="sm"
              variant="ghost"
              className="h-7 text-xs gap-1 text-muted-foreground group-hover:bg-secondary group-hover:text-secondary-foreground transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                onFindSimilar(video.video_id);
              }}
            >
              <Sparkles className="w-3 h-3" />
              Similar
            </Button>
          )}
          {video.source_url && (
            <a
              href={video.source_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="ml-auto"
            >
              <Button size="sm" variant="ghost" className="h-7 text-xs text-muted-foreground hover:text-foreground">
                <ExternalLink className="w-3 h-3" />
              </Button>
            </a>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
