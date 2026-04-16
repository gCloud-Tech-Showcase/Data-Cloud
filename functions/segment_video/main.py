"""
Cloud Function: Video Segmentation

Triggered by GCS object finalization in the video search bucket.
When a video is uploaded to raw/*.mp4, this function:
1. Downloads the video to /tmp
2. Splits it into 2-minute segments using ffmpeg
3. Uploads segments to segments/{video_id}/seg_NNN.mp4
4. Writes a per-video metadata CSV to manifests/metadata/{video_id}.csv
5. Attaches parent video metadata to each segment as GCS custom metadata

Only processes files matching raw/*.mp4 — ignores everything else
to prevent infinite trigger loops from segment uploads.
"""

import csv
import io
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

import functions_framework
import requests as http_requests
from cloudevents.http import CloudEvent
from google.cloud import storage
import google.auth
import google.auth.transport.requests

SEGMENT_DURATION = 120  # seconds
DATAFORM_REPO = "projects/gcloud-tech-showcase/locations/us-central1/repositories/data-cloud"
# TODO: Switch to "production" after merging to main
DATAFORM_RELEASE_CONFIG = f"{DATAFORM_REPO}/releaseConfigs/video-search-dev"

METADATA_CSV_COLUMNS = [
    "video_id", "identifier", "title", "year", "source_url",
    "license", "segment_index", "start_seconds", "end_seconds",
    "duration_total_seconds",
]

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def trigger_dataform_pipeline() -> None:
    """Trigger a Dataform workflow to generate embeddings for new segments.

    Uses the latest compilation result from the production release config
    and runs only the video_vector_search tagged tables.
    """
    try:
        credentials, _ = google.auth.default()
        credentials.refresh(google.auth.transport.requests.Request())
        token = credentials.token

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Get the latest compilation result from the release config
        release_url = f"https://dataform.googleapis.com/v1beta1/{DATAFORM_RELEASE_CONFIG}"
        resp = http_requests.get(release_url, headers=headers, timeout=10)
        resp.raise_for_status()
        compilation_result = resp.json().get("releaseCompilationResult")

        if not compilation_result:
            logger.error("No compilation result found in release config")
            return

        # Create a workflow invocation for video_vector_search tables only
        invoke_url = f"https://dataform.googleapis.com/v1beta1/{DATAFORM_REPO}/workflowInvocations"
        body = {
            "compilationResult": compilation_result,
            "invocationConfig": {
                "includedTags": ["video_vector_search"],
                "transitiveDependenciesIncluded": True,
                "fullyRefreshIncrementalTablesEnabled": False,
            },
        }
        resp = http_requests.post(invoke_url, headers=headers, json=body, timeout=10)
        resp.raise_for_status()

        invocation = resp.json().get("name", "")
        logger.info(f"Triggered Dataform pipeline: {invocation}")

    except Exception as e:
        logger.error(f"Failed to trigger Dataform: {e}")


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
        logger.error(f"ffprobe failed: {result.stderr}")
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
        logger.error(f"ffmpeg failed: {result.stderr}")
        return []

    return sorted(output_dir.glob("seg_*.mp4"))


@functions_framework.cloud_event
def segment_video(cloud_event: CloudEvent) -> None:
    """Handle GCS object finalization event."""
    data = cloud_event.data

    bucket_name = data["bucket"]
    object_name = data["name"]

    # Only process raw/*.mp4 files — ignore everything else
    if not object_name.startswith("raw/") or not object_name.lower().endswith(".mp4"):
        logger.info(f"Ignoring non-raw-video object: {object_name}")
        return

    # Extract video_id from filename: raw/{video_id}.mp4
    video_id = Path(object_name).stem
    logger.info(f"Processing video: {video_id} from {object_name}")

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

    logger.info(f"Metadata: title={title}, year={year}, identifier={identifier}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Download video
        video_path = tmpdir_path / f"{video_id}.mp4"
        logger.info(f"Downloading gs://{bucket_name}/{object_name}")
        blob.download_to_filename(str(video_path))

        # Get duration
        duration = get_video_duration(video_path)
        logger.info(f"Duration: {duration:.1f}s ({duration / 60:.1f} min)")

        if duration == 0:
            logger.error(f"Could not determine duration for {video_id}")
            return

        # Split
        segments_dir = tmpdir_path / "segments"
        logger.info(f"Splitting into {SEGMENT_DURATION}s segments...")
        segments = split_video(video_path, segments_dir)

        if not segments:
            logger.error(f"No segments produced for {video_id}")
            return

        logger.info(f"Produced {len(segments)} segments")

        # Upload segments with parent metadata attached
        segment_metadata = {
            "video_id": video_id,
            "identifier": identifier,
            "title": title,
            "year": year,
            "source_url": source_url,
            "license": license_str,
        }

        metadata_rows = []
        for i, seg_path in enumerate(segments):
            gcs_path = f"segments/{video_id}/seg_{i:03d}.mp4"
            seg_blob = bucket.blob(gcs_path)
            seg_blob.metadata = segment_metadata
            seg_blob.upload_from_filename(str(seg_path))
            logger.info(f"  Uploaded segment {i}: {gcs_path}")

            start_seconds = i * SEGMENT_DURATION
            end_seconds = min((i + 1) * SEGMENT_DURATION, int(duration))

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
            logger.info(f"  Thumbnail: gs://{bucket_name}/thumbnails/{video_id}.jpg")

        # Write metadata CSV
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=METADATA_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(metadata_rows)

        csv_path = f"manifests/metadata/{video_id}.csv"
        csv_blob = bucket.blob(csv_path)
        csv_blob.upload_from_string(buf.getvalue(), content_type="text/csv")
        logger.info(f"  Metadata CSV: gs://{bucket_name}/{csv_path}")

    logger.info(
        f"Done: {video_id} — {len(segments)} segments, "
        f"{duration:.0f}s total duration"
    )

    # Trigger Dataform to generate embeddings for the new segments
    trigger_dataform_pipeline()
