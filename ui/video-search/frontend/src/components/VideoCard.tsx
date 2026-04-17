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
}

export function VideoCard({ video, onPlay, onFindSimilar }: VideoCardProps) {
  const bestSegment = video.top_segments[0] || { segment_index: 0, start_seconds: 0, end_seconds: 120, distance: 0 };

  return (
    <Card className="overflow-hidden group hover:shadow-md transition-shadow duration-200">
      {/* Thumbnail — 16:9 aspect ratio */}
      <div
        className="relative aspect-video bg-muted cursor-pointer"
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

        {/* Match badge — only when searching */}
        {video.relevance_pct > 0 && (
          <Badge
            variant="secondary"
            className="absolute top-2 right-2 bg-background/80 backdrop-blur-sm"
          >
            {video.relevance_pct}% match
          </Badge>
        )}

        {/* Duration badge — bottom right of thumbnail */}
        {video.duration_total_seconds && (
          <span className="absolute bottom-2 right-2 bg-black/70 text-white text-xs px-1.5 py-0.5 rounded">
            {formatDuration(video.duration_total_seconds)}
          </span>
        )}
      </div>

      <CardContent className="p-3 space-y-1">
        {/* Title + year — always visible */}
        <h3 className="text-sm font-medium text-foreground line-clamp-1">
          {video.title}
        </h3>
        <p className="text-xs text-muted-foreground">
          {video.year && <span>{video.year}</span>}
          {video.category && (
            <span className="ml-2 capitalize">{video.category}</span>
          )}
        </p>

        {/* Description — visible on hover */}
        {video.ai_description && (
          <p className="text-xs text-muted-foreground line-clamp-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            {video.ai_description}
          </p>
        )}

        {/* Match info — only when searching */}
        {video.matching_intervals > 0 && (
          <p className="text-[11px] text-muted-foreground/70">
            Best match at {formatDuration(bestSegment.start_seconds)}–{formatDuration(bestSegment.end_seconds)}
          </p>
        )}

        {/* Actions — visible on hover */}
        <div className="flex gap-1.5 pt-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
          <Button
            size="sm"
            variant="default"
            className="h-7 text-xs gap-1"
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
              variant="secondary"
              className="h-7 text-xs gap-1"
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
            >
              <Button size="sm" variant="ghost" className="h-7 text-xs gap-1">
                <ExternalLink className="w-3 h-3" />
              </Button>
            </a>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
