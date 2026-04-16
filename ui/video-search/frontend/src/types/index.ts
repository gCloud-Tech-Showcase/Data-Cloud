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

export interface LibraryStats {
  total_videos: number;
  total_embeddings: number;
  earliest_year: number | null;
  latest_year: number | null;
  categories: { name: string; count: number }[];
}

export interface ArchiveItem {
  identifier: string;
  title: string;
  year: number | null;
  description: string;
  collection: string;
  thumbnail_url: string;
  source_url: string;
}

export interface ArchiveSearchResponse {
  query: string;
  results: ArchiveItem[];
  total_results: number;
}

export interface ArchiveItemDetails {
  identifier: string;
  title: string;
  year: number | null;
  video_id: string;
  source_url: string;
  download_url: string;
  thumbnail_url: string;
  file_size_bytes: number;
  file_size_mb: number;
  mp4_filename: string;
}

export interface IngestResponse {
  status: string;
  video_id: string;
  title: string;
  message: string;
}

export interface SimilarResponse {
  source_video_id: string;
  results: VideoResult[];
  total_results: number;
  search_time_ms: number;
}
