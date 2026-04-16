import { X, Clock } from "lucide-react";
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
  onSegmentChange: (segmentIndex: number) => void;
  onClose: () => void;
}

export function VideoPlayer({
  title,
  videoUrl,
  segments,
  activeSegment,
  onSegmentChange,
  onClose,
}: VideoPlayerProps) {
  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-card rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-medium text-foreground truncate">
            {title}
          </h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>

        <div className="aspect-video bg-black">
          <video
            key={videoUrl}
            controls
            autoPlay
            className="w-full h-full"
          >
            <source src={videoUrl} type="video/mp4" />
          </video>
        </div>

        {segments.length > 1 && (
          <div className="p-4 border-t border-border">
            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-2">
              Matching segments
            </p>
            <div className="flex flex-wrap gap-2">
              {segments.map((seg) => (
                <Badge
                  key={seg.segment_index}
                  variant={seg.segment_index === activeSegment ? "default" : "secondary"}
                  className="cursor-pointer gap-1"
                  onClick={() => onSegmentChange(seg.segment_index)}
                >
                  <Clock className="w-3 h-3" />
                  {formatDuration(seg.start_seconds)}–{formatDuration(seg.end_seconds)}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
