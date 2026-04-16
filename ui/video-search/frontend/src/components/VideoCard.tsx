import { Play, ExternalLink, Clock, Sparkles } from "lucide-react";
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
  const bestSegment = video.top_segments[0];

  return (
    <Card className="overflow-hidden hover:shadow-md transition-shadow duration-200 group">
      <div
        className="relative aspect-video bg-muted cursor-pointer"
        onClick={() => bestSegment && onPlay(video.video_id, bestSegment.segment_index)}
      >
        <img
          src={video.thumbnail_url}
          alt={video.title}
          className="w-full h-full object-cover"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors duration-200 flex items-center justify-center">
          <Play className="w-12 h-12 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-200 drop-shadow-lg" />
        </div>
        <Badge
          variant="secondary"
          className="absolute top-2 right-2 bg-background/80 backdrop-blur-sm"
        >
          {video.relevance_pct}% match
        </Badge>
      </div>

      <CardContent className="p-4 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="text-lg font-medium text-foreground truncate">
              {video.title}
            </h3>
            <p className="text-sm text-muted-foreground">
              {video.year && <span>{video.year}</span>}
              {video.duration_total_seconds && (
                <span className="ml-2">
                  <Clock className="w-3 h-3 inline -mt-0.5 mr-0.5" />
                  {formatDuration(video.duration_total_seconds)}
                </span>
              )}
            </p>
          </div>
        </div>

        {bestSegment && (
          <p className="text-xs text-muted-foreground">
            Best match at {formatDuration(bestSegment.start_seconds)}–
            {formatDuration(bestSegment.end_seconds)}
            <span className="ml-1 text-muted-foreground/60">
              ({video.matching_intervals} matching intervals)
            </span>
          </p>
        )}

        <div className="flex gap-2 pt-1">
          {bestSegment && (
            <Button
              size="sm"
              variant="default"
              className="gap-1.5"
              onClick={() => onPlay(video.video_id, bestSegment.segment_index)}
            >
              <Play className="w-3.5 h-3.5" />
              Play segment
            </Button>
          )}
          {onFindSimilar && (
            <Button
              size="sm"
              variant="secondary"
              className="gap-1.5"
              onClick={() => onFindSimilar(video.video_id)}
            >
              <Sparkles className="w-3.5 h-3.5" />
              Similar
            </Button>
          )}
          {video.source_url && (
            <a href={video.source_url} target="_blank" rel="noopener noreferrer">
              <Button size="sm" variant="ghost" className="gap-1.5">
                <ExternalLink className="w-3.5 h-3.5" />
                Source
              </Button>
            </a>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
