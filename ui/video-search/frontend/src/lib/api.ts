import type { SearchResponse, VideosResponse, PlaybackResponse } from "@/types";

const BASE = "";

export async function searchVideos(
  query: string,
  limit = 20
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  const res = await fetch(`${BASE}/api/search?${params}`);
  if (!res.ok) throw new Error(`Search failed: ${res.statusText}`);
  return res.json();
}

export async function listVideos(): Promise<VideosResponse> {
  const res = await fetch(`${BASE}/api/videos`);
  if (!res.ok) throw new Error(`Failed to list videos: ${res.statusText}`);
  return res.json();
}

export async function getPlaybackUrl(
  videoId: string,
  segmentIndex: number
): Promise<PlaybackResponse> {
  const res = await fetch(
    `${BASE}/api/videos/${videoId}/segments/${segmentIndex}/play`
  );
  if (!res.ok) throw new Error(`Failed to get playback URL: ${res.statusText}`);
  return res.json();
}

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}
