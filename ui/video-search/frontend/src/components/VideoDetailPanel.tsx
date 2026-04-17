import { useEffect, useState } from "react";
import {
  X, Play, ExternalLink, Sparkles, Film, Eye, Music,
  MessageSquare, Users, MapPin, Gauge, AlertTriangle, Tag
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { getVideoDetails, formatDuration } from "@/lib/api";
import type { VideoDetails } from "@/types";

interface VideoDetailPanelProps {
  videoId: string;
  onClose: () => void;
  onPlay: (videoId: string) => void;
  onFindSimilar: (videoId: string) => void;
}

export function VideoDetailPanel({ videoId, onClose, onPlay, onFindSimilar }: VideoDetailPanelProps) {
  const [details, setDetails] = useState<VideoDetails | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getVideoDetails(videoId)
      .then(setDetails)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [videoId]);

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />

      {/* Panel */}
      <div className="relative w-full max-w-lg bg-background shadow-2xl overflow-y-auto animate-in slide-in-from-right">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-background/95 backdrop-blur border-b border-border px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-medium text-foreground truncate pr-4">
            {details?.title || videoId}
          </h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>

        {loading ? (
          <div className="p-6 space-y-4">
            <Skeleton className="aspect-video rounded-lg" />
            <Skeleton className="h-6 w-3/4" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
            <div className="grid grid-cols-2 gap-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-16 rounded-lg" />
              ))}
            </div>
          </div>
        ) : details ? (
          <div className="p-6 space-y-6">
            {/* Thumbnail + play */}
            <div className="relative aspect-video rounded-lg overflow-hidden bg-muted group cursor-pointer"
              onClick={() => onPlay(videoId)}
            >
              <img
                src={details.thumbnail_url}
                alt={details.title}
                className="w-full h-full object-cover"
                onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
              />
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center">
                <Play className="w-16 h-16 text-white opacity-0 group-hover:opacity-100 transition-opacity drop-shadow-lg" />
              </div>
              {details.duration_total_seconds && (
                <span className="absolute bottom-2 right-2 bg-black/70 text-white text-sm px-2 py-0.5 rounded">
                  {formatDuration(details.duration_total_seconds)}
                </span>
              )}
            </div>

            {/* Title + year + actions */}
            <div>
              <h3 className="text-xl font-semibold text-foreground">{details.title}</h3>
              <p className="text-sm text-muted-foreground mt-1">
                {details.year && <span>{details.year}</span>}
                {details.duration_total_seconds && (
                  <span className="ml-2">{formatDuration(details.duration_total_seconds)}</span>
                )}
              </p>
              <div className="flex gap-2 mt-3">
                <Button size="sm" className="gap-1.5" onClick={() => onPlay(videoId)}>
                  <Play className="w-3.5 h-3.5" />
                  Play video
                </Button>
                <Button size="sm" variant="secondary" className="gap-1.5" onClick={() => onFindSimilar(videoId)}>
                  <Sparkles className="w-3.5 h-3.5" />
                  Find similar
                </Button>
                {details.source_url && (
                  <a href={details.source_url} target="_blank" rel="noopener noreferrer">
                    <Button size="sm" variant="ghost" className="gap-1.5">
                      <ExternalLink className="w-3.5 h-3.5" />
                    </Button>
                  </a>
                )}
              </div>
            </div>

            {/* AI Description */}
            {details.ai_description && (
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5 text-xs text-primary/60">
                  <Sparkles className="w-3 h-3" />
                  <span>AI-generated description</span>
                </div>
                <p className="text-sm text-foreground leading-relaxed">
                  {details.ai_description}
                </p>
              </div>
            )}

            {/* Metadata grid */}
            <div className="grid grid-cols-2 gap-3">
              <MetadataCard icon={Film} label="Category" value={details.category} />
              <MetadataCard icon={Eye} label="Mood" value={details.mood} />
              <MetadataCard icon={Film} label="Color" value={details.color_mode?.replace("_", " ")} />
              <MetadataCard icon={Film} label="Style" value={details.style} />
              <MetadataCard icon={MessageSquare} label="Language" value={details.language} />
              <MetadataCard icon={Users} label="Audience" value={details.target_audience} />
              <MetadataCard icon={MapPin} label="Setting" value={details.setting} />
              <MetadataCard icon={Gauge} label="Pacing" value={details.pacing} />
              <MetadataCard icon={MessageSquare} label="Dialogue" value={details.has_dialogue ? "Yes" : "No"} />
              <MetadataCard icon={Music} label="Music" value={details.has_music ? "Yes" : "No"} />
            </div>

            {/* Themes */}
            {details.themes.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Tag className="w-3 h-3" />
                  <span>Themes</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {details.themes.map((theme) => (
                    <Badge key={theme} variant="secondary" className="capitalize">
                      {theme.replace(/"/g, "")}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Characters */}
            {details.characters.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Users className="w-3 h-3" />
                  <span>Characters</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {details.characters.map((char) => (
                    <Badge key={char} variant="outline" className="capitalize">
                      {char.replace(/"/g, "")}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Content warnings */}
            {details.content_warnings.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-1.5 text-xs text-amber-600">
                  <AlertTriangle className="w-3 h-3" />
                  <span>Content warnings</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {details.content_warnings.map((warning) => (
                    <Badge key={warning} variant="outline" className="text-amber-700 border-amber-200 bg-amber-50">
                      {warning.replace(/"/g, "")}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Footer */}
            <div className="pt-4 border-t border-border">
              <p className="flex items-center gap-1.5 text-[10px] text-primary/50">
                <Sparkles className="w-3 h-3" />
                All metadata AI-generated by Gemini 2.5 Flash
              </p>
            </div>
          </div>
        ) : (
          <div className="p-6 text-center text-muted-foreground">
            Video not found
          </div>
        )}
      </div>
    </div>
  );
}

function MetadataCard({ icon: Icon, label, value }: { icon: any; label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div className="bg-muted/50 rounded-lg p-3 space-y-1">
      <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground uppercase tracking-wider">
        <Icon className="w-3 h-3" />
        {label}
      </div>
      <p className="text-sm font-medium text-foreground capitalize">{value}</p>
    </div>
  );
}
