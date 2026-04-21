"""
Cloud Function: Video Segmentation

Triggered by GCS object finalization in the video search bucket.
When a video is uploaded to raw/*.mp4, this function:
1. Downloads the video to /tmp
2. Splits it into 2-minute segments using ffmpeg
3. Uploads segments with full metadata (title, year, timing, etc.)
4. Extracts a thumbnail frame

Embedding generation and AI metadata extraction are handled by the
scheduled Dataform pipeline — not by this function. This keeps the
function fast and focused on media processing only.

Only processes files matching raw/*.mp4 — ignores everything else
to prevent infinite trigger loops from segment uploads.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import functions_framework
from cloudevents.http import CloudEvent
from google.cloud import storage

SEGMENT_DURATION = 120  # seconds


def log(message: str) -> None:
    """Write log to stdout for Cloud Logging to capture."""
    print(message, flush=True)


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

        # Upload segments with full metadata per segment
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

    log(
        f"Done: {video_id} — {len(segments)} segments, "
        f"{duration:.0f}s total duration"
    )
