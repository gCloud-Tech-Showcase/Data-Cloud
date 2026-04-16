export interface VideoSegment {
  segment_index: number;
  start_seconds: number;
  end_seconds: number;
  distance: number;
}

export interface VideoResult {
  video_id: string;
  title: string;
  year: number | null;
  source_url: string;
  duration_total_seconds: number | null;
  thumbnail_url: string;
  best_distance: number;
  relevance_pct: number;
  matching_intervals: number;
  top_segments: VideoSegment[];
}

export interface SearchResponse {
  query: string;
  results: VideoResult[];
  total_results: number;
  search_time_ms: number;
}

export interface VideoListItem {
  video_id: string;
  title: string;
  year: number | null;
  source_url: string;
  duration_total_seconds: number | null;
  thumbnail_url: string;
}

export interface VideosResponse {
  videos: VideoListItem[];
}

export interface PlaybackResponse {
  video_id: string;
  segment_index: number;
  url: string;
}
