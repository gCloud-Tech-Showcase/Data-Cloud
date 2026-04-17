"""
Cloud Function: Video Segmentation + Embedding

Triggered by GCS object finalization in the video search bucket.
When a video is uploaded to raw/*.mp4, this function:
1. Downloads the video to /tmp
2. Splits it into 2-minute segments using ffmpeg
3. Uploads segments to segments/{video_id}/seg_NNN.mp4
4. Writes a per-video metadata CSV to manifests/metadata/{video_id}.csv
5. Extracts a thumbnail frame to thumbnails/{video_id}.jpg
6. Attaches parent video metadata to each segment as GCS custom metadata
7. Refreshes BQ external table metadata cache
8. Generates multimodal embeddings for the new segments
9. Rebuilds the gold search table

Only processes files matching raw/*.mp4 — ignores everything else
to prevent infinite trigger loops from segment uploads.
"""

import csv
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import functions_framework
from cloudevents.http import CloudEvent
from google.cloud import bigquery, storage


def log(message: str) -> None:
    """Write log to stdout for Cloud Logging to capture."""
    print(message, flush=True)

SEGMENT_DURATION = 120  # seconds

METADATA_CSV_COLUMNS = [
    "video_id", "identifier", "title", "year", "source_url",
    "license", "segment_index", "start_seconds", "end_seconds",
    "duration_total_seconds",
]

PROJECT_ID = os.environ.get("GCP_PROJECT", "gcloud-tech-showcase")
DATASET = "video_vector_search"



def get_video_duration(video_path: Path) -> float:
    """Get video duration in seconds using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(video_path),
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        log(f"ffprobe failed: {result.stderr}")
        return 0.0

    data = json.loads(result.stdout)
    return float(data.get("format", {}).get("duration", 0))


def split_video(video_path: Path, output_dir: Path) -> list[Path]:
    """Split a video into 2-minute segments using ffmpeg."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = str(output_dir / "seg_%03d.mp4")

    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-c", "copy",
            "-map", "0",
            "-segment_time", str(SEGMENT_DURATION),
            "-f", "segment",
            "-reset_timestamps", "1",
            output_pattern,
        ],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        log(f"ffmpeg failed: {result.stderr}")
        return []

    return sorted(output_dir.glob("seg_*.mp4"))


def generate_embeddings(video_id: str) -> None:
    """Generate embeddings for a video's segments and update search tables."""
    client = bigquery.Client(project=PROJECT_ID)

    # Refresh external table cache so new segments are visible
    log("Refreshing metadata cache...")
    client.query(
        f"CALL BQ.REFRESH_EXTERNAL_METADATA_CACHE('{DATASET}.bronze_video_segments')"
    ).result()

    # Generate embeddings for this video's segments
    log(f"Generating embeddings for {video_id}...")
    embed_sql = f"""
    INSERT INTO `{DATASET}.silver_segment_embeddings`
      (segment_uri, video_id, segment_index, embedding, status, video_start_sec, video_end_sec)
    SELECT
      uri AS segment_uri,
      REGEXP_EXTRACT(uri, r'/segments/([^/]+)/') AS video_id,
      CAST(REGEXP_EXTRACT(uri, r'seg_(\\d+)\\.mp4') AS INT64) AS segment_index,
      embedding,
      status,
      video_start_sec,
      video_end_sec
    FROM AI.GENERATE_EMBEDDING(
      MODEL `{DATASET}.multimodal_embedding_model`,
      (SELECT * FROM `{DATASET}.bronze_video_segments`
       WHERE uri LIKE '%/segments/{video_id}/%')
    )
    """
    client.query(embed_sql).result()
    log(f"Embeddings generated for {video_id}")

    # Extract metadata using Gemini 2.5 Flash via AI.GENERATE + OBJ.GET_ACCESS_URL
    log(f"Extracting metadata for {video_id}...")
    meta_sql = f"""
    MERGE INTO `{DATASET}.silver_video_metadata` T
    USING (
      SELECT
        REGEXP_EXTRACT(uri, r'/segments/([^/]+)/') AS video_id,
        r.category, r.mood, r.color_mode, r.style, r.description, r.themes, r.characters
      FROM `{DATASET}.bronze_video_segments`,
      UNNEST([
        AI.GENERATE(
          (OBJ.GET_ACCESS_URL(ref, 'r'),
           'Classify this video. category: cartoon, educational, documentary, newsreel, or other. mood: humorous, dramatic, educational, suspenseful, lighthearted, or serious. color_mode: color or black_and_white. style: hand-drawn animation, stop motion, live action, or mixed. description: one sentence about the main action. themes: 2-4 themes. characters: character names if identifiable.'),
          connection_id => 'us.vertex-ai-connection',
          endpoint => 'gemini-2.5-flash',
          output_schema => 'category STRING, mood STRING, color_mode STRING, style STRING, description STRING, themes ARRAY<STRING>, characters ARRAY<STRING>'
        )
      ]) AS r
      WHERE uri LIKE '%/segments/{video_id}/seg_000.mp4'
    ) S
    ON T.video_id = S.video_id
    WHEN MATCHED THEN UPDATE SET
      category = S.category, mood = S.mood, color_mode = S.color_mode,
      style = S.style, description = S.description, themes = S.themes, characters = S.characters
    WHEN NOT MATCHED THEN INSERT
      (video_id, category, mood, color_mode, style, description, themes, characters)
      VALUES (S.video_id, S.category, S.mood, S.color_mode, S.style, S.description, S.themes, S.characters)
    """
    try:
        client.query(meta_sql).result()
        log(f"Metadata extracted for {video_id}")
    except Exception as e:
        log(f"Metadata extraction failed (non-fatal): {e}")

    # Rebuild gold table using object metadata + AI metadata
    log("Rebuilding gold table...")
    gold_sql = f"""
    CREATE OR REPLACE TABLE `{DATASET}.gold_searchable_videos` AS
    WITH segment_metadata AS (
      SELECT
        uri,
        (SELECT value FROM UNNEST(metadata) WHERE name = 'title') AS title,
        SAFE_CAST((SELECT value FROM UNNEST(metadata) WHERE name = 'year') AS INT64) AS year,
        (SELECT value FROM UNNEST(metadata) WHERE name = 'source_url') AS source_url,
        (SELECT value FROM UNNEST(metadata) WHERE name = 'license') AS license,
        SAFE_CAST((SELECT value FROM UNNEST(metadata) WHERE name = 'start_seconds') AS INT64) AS start_seconds,
        SAFE_CAST((SELECT value FROM UNNEST(metadata) WHERE name = 'end_seconds') AS INT64) AS end_seconds,
        SAFE_CAST((SELECT value FROM UNNEST(metadata) WHERE name = 'duration_total_seconds') AS INT64) AS duration_total_seconds
      FROM `{DATASET}.bronze_video_segments`
    )
    SELECT
      e.segment_uri,
      e.video_id,
      e.segment_index,
      COALESCE(sm.title, e.video_id) AS title,
      sm.year,
      sm.source_url,
      sm.license,
      sm.duration_total_seconds,
      sm.start_seconds,
      sm.end_seconds,
      e.video_start_sec,
      e.video_end_sec,
      vm.category,
      vm.mood,
      vm.color_mode,
      vm.style,
      vm.description AS ai_description,
      e.embedding
    FROM `{DATASET}.silver_segment_embeddings` e
    LEFT JOIN segment_metadata sm
      ON e.segment_uri = sm.uri
    LEFT JOIN `{DATASET}.silver_video_metadata` vm
      ON e.video_id = vm.video_id
    """
    client.query(gold_sql).result()
    log("Gold table rebuilt")


@functions_framework.cloud_event
def segment_video(cloud_event: CloudEvent) -> None:
    """Handle GCS object finalization event."""
    data = cloud_event.data

    bucket_name = data["bucket"]
    object_name = data["name"]

    # Only process raw/*.mp4 files — ignore everything else
    if not object_name.startswith("raw/") or not object_name.lower().endswith(".mp4"):
        log(f"Ignoring non-raw-video object: {object_name}")
        return

    # Extract video_id from filename: raw/{video_id}.mp4
    video_id = Path(object_name).stem
    log(f"Processing video: {video_id} from {object_name}")

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    # Read custom metadata from the uploaded object
    blob = bucket.blob(object_name)
    blob.reload()
    custom_metadata = blob.metadata or {}

    title = custom_metadata.get("title", video_id)
    year = custom_metadata.get("year", "")
    identifier = custom_metadata.get("identifier", video_id)
    source_url = custom_metadata.get("source_url", "")
    license_str = custom_metadata.get("license", "Public Domain")

    log(f"Metadata: title={title}, year={year}, identifier={identifier}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Download video
        video_path = tmpdir_path / f"{video_id}.mp4"
        log(f"Downloading gs://{bucket_name}/{object_name}")
        blob.download_to_filename(str(video_path))

        # Get duration
        duration = get_video_duration(video_path)
        log(f"Duration: {duration:.1f}s ({duration / 60:.1f} min)")

        if duration == 0:
            log(f"Could not determine duration for {video_id}")
            return

        # Split
        segments_dir = tmpdir_path / "segments"
        log(f"Splitting into {SEGMENT_DURATION}s segments...")
        segments = split_video(video_path, segments_dir)

        if not segments:
            log(f"No segments produced for {video_id}")
            return

        log(f"Produced {len(segments)} segments")

        # Upload segments with full metadata attached per segment
        metadata_rows = []
        for i, seg_path in enumerate(segments):
            start_seconds = i * SEGMENT_DURATION
            end_seconds = min((i + 1) * SEGMENT_DURATION, int(duration))

            segment_metadata = {
                "video_id": video_id,
                "identifier": identifier,
                "title": title,
                "year": year,
                "source_url": source_url,
                "license": license_str,
                "segment_index": str(i),
                "start_seconds": str(start_seconds),
                "end_seconds": str(end_seconds),
                "duration_total_seconds": str(int(duration)),
            }

            gcs_path = f"segments/{video_id}/seg_{i:03d}.mp4"
            seg_blob = bucket.blob(gcs_path)
            seg_blob.metadata = segment_metadata
            seg_blob.upload_from_filename(str(seg_path))
            log(f"  Uploaded segment {i}: {gcs_path}")

            metadata_rows.append({
                "video_id": video_id,
                "identifier": identifier,
                "title": title,
                "year": year,
                "source_url": source_url,
                "license": license_str,
                "segment_index": i,
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
                "duration_total_seconds": int(duration),
            })

        # Extract thumbnail from first segment
        thumbnail_path = tmpdir_path / f"{video_id}.jpg"
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(segments[0]),
                "-ss", "5",
                "-frames:v", "1",
                "-q:v", "2",
                str(thumbnail_path),
            ],
            capture_output=True, text=True,
        )
        if thumbnail_path.exists():
            thumb_blob = bucket.blob(f"thumbnails/{video_id}.jpg")
            thumb_blob.upload_from_filename(str(thumbnail_path))
            log(f"  Thumbnail: gs://{bucket_name}/thumbnails/{video_id}.jpg")

        # Write metadata CSV
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=METADATA_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(metadata_rows)

        csv_path = f"manifests/metadata/{video_id}.csv"
        csv_blob = bucket.blob(csv_path)
        csv_blob.upload_from_string(buf.getvalue(), content_type="text/csv")
        log(f"  Metadata CSV: gs://{bucket_name}/{csv_path}")

    log(
        f"Segmentation complete: {video_id} — {len(segments)} segments, "
        f"{duration:.0f}s total duration"
    )

    # Generate embeddings and update search tables
    try:
        generate_embeddings(video_id)
    except Exception as e:
        log(f"Embedding generation failed for {video_id}: {e}")
        log("Video is segmented but not yet searchable. Run Dataform to generate embeddings.")
