import type { SearchResponse, VideosResponse, LibraryStats, SimilarResponse, ArchiveSearchResponse, IngestResponse, VideoDetails } from "@/types";

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

export function getSegmentPlayUrl(videoId: string, segmentIndex: number): string {
  return `${BASE}/api/videos/${videoId}/segments/${segmentIndex}/play`;
}

export function getFullVideoUrl(videoId: string): string {
  return `${BASE}/api/videos/${videoId}/play`;
}

export async function getLibraryStats(): Promise<LibraryStats> {
  const res = await fetch(`${BASE}/api/videos/stats`);
  if (!res.ok) throw new Error(`Failed to get stats: ${res.statusText}`);
  return res.json();
}

export async function findSimilar(
  videoId: string,
  limit = 10
): Promise<SimilarResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  const res = await fetch(`${BASE}/api/videos/${videoId}/similar?${params}`);
  if (!res.ok) throw new Error(`Failed to find similar: ${res.statusText}`);
  return res.json();
}

export async function searchArchive(
  query: string,
  limit = 20
): Promise<ArchiveSearchResponse> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  const res = await fetch(`${BASE}/api/archive/search?${params}`);
  if (!res.ok) throw new Error(`Archive search failed: ${res.statusText}`);
  return res.json();
}

export async function ingestFromArchive(
  identifier: string
): Promise<IngestResponse> {
  const res = await fetch(`${BASE}/api/archive/${identifier}/ingest`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Ingest failed: ${res.statusText}`);
  return res.json();
}

export async function getVideoDetails(videoId: string): Promise<VideoDetails> {
  const res = await fetch(`${BASE}/api/videos/${videoId}/details`);
  if (!res.ok) throw new Error(`Failed to get details: ${res.statusText}`);
  return res.json();
}

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}
