#!/usr/bin/env python3
"""
Video Segmentation Script

Splits videos into 2-minute (120-second) segments for embedding generation.
AI.GENERATE_EMBEDDING in BigQuery only analyzes the first 120 seconds of any
video, so splitting into segments ensures full coverage of longer videos.

Supports two input modes:
- GCS (default): Downloads videos from gs://{project}-video-search/raw/,
  splits them, and uploads segments to gs://{project}-video-search/segments/
- Local: Reads videos from a local directory (--local-dir), useful for
  testing without the GCS round-trip.

Also builds a segment mapping table and loads it to BigQuery for joining
segments back to their parent videos at query time.

Usage:
    # Process all videos from GCS (reads manifest for video list)
    python segment_videos.py --project PROJECT_ID

    # Process specific video(s)
    python segment_videos.py --project PROJECT_ID --video-id popeye-for-president

    # Process from local files (skip GCS download)
    python segment_videos.py --project PROJECT_ID --local-dir ./video_staging

    # Dry run — show what would be processed
    python segment_videos.py --project PROJECT_ID --dry-run

    # Check progress
    python segment_videos.py --status
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from google.cloud import bigquery, storage
from tqdm import tqdm

# Configuration
SCRIPT_DIR = Path(__file__).parent
MANIFEST_FILE = SCRIPT_DIR / "video_manifest.json"
SEGMENT_CHECKPOINT_FILE = SCRIPT_DIR / "segment_checkpoint.json"
LOG_FILE = SCRIPT_DIR / "segment_videos.log"
SEGMENT_DURATION = 120  # seconds
BUCKET_SUFFIX = "-video-search"
BQ_DATASET = "video_vector_search"
BQ_TABLE = "bronze_segment_mapping"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------

def check_ffmpeg() -> None:
    """Verify ffmpeg is installed."""
    if not shutil.which("ffmpeg"):
        logger.error(
            "ffmpeg not found. Install it:\n"
            "  apt install ffmpeg    (Debian/Ubuntu)\n"
            "  brew install ffmpeg   (macOS)"
        )
        sys.exit(1)

    if not shutil.which("ffprobe"):
        logger.error("ffprobe not found (usually installed with ffmpeg)")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------

def load_checkpoint() -> dict[str, Any]:
    """Load segmentation checkpoint."""
    if SEGMENT_CHECKPOINT_FILE.exists():
        try:
            with open(SEGMENT_CHECKPOINT_FILE, "r") as f:
                checkpoint = json.load(f)
                logger.info(
                    f"Loaded checkpoint: {len(checkpoint.get('completed_ids', []))} "
                    f"videos segmented"
                )
                return checkpoint
        except json.JSONDecodeError:
            backup = f"{SEGMENT_CHECKPOINT_FILE}.corrupted"
            SEGMENT_CHECKPOINT_FILE.rename(backup)
            logger.warning(f"Corrupted checkpoint backed up to {backup}")

    return {
        "completed_ids": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": None,
    }


def save_checkpoint(checkpoint: dict[str, Any]) -> None:
    """Save checkpoint."""
    checkpoint["last_updated"] = datetime.now(timezone.utc).isoformat()
    with open(SEGMENT_CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoint, f, indent=2)


# ---------------------------------------------------------------------------
# Video duration
# ---------------------------------------------------------------------------

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
        logger.warning(f"ffprobe failed for {video_path}: {result.stderr}")
        return 0.0

    data = json.loads(result.stdout)
    return float(data.get("format", {}).get("duration", 0))


# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------

def split_video(video_path: Path, output_dir: Path) -> list[Path]:
    """Split a video into segments using ffmpeg.

    Returns list of segment file paths.
    """
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
        logger.error(f"ffmpeg failed for {video_path}: {result.stderr}")
        return []

    segments = sorted(output_dir.glob("seg_*.mp4"))
    return segments


# ---------------------------------------------------------------------------
# GCS operations
# ---------------------------------------------------------------------------

def download_from_gcs(bucket_name: str, gcs_path: str, local_path: Path) -> bool:
    """Download a file from GCS."""
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(local_path))
        return True
    except Exception as e:
        logger.error(f"GCS download failed for {gcs_path}: {e}")
        return False


def upload_to_gcs(bucket_name: str, local_path: Path, gcs_path: str) -> bool:
    """Upload a file to GCS."""
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_path)
        blob.upload_from_filename(str(local_path))
        return True
    except Exception as e:
        logger.error(f"GCS upload failed for {gcs_path}: {e}")
        return False


# ---------------------------------------------------------------------------
# BigQuery segment mapping
# ---------------------------------------------------------------------------

def load_segment_mapping_to_bq(
    project_id: str, mapping_rows: list[dict[str, Any]]
) -> None:
    """Load segment mapping rows to BigQuery."""
    if not mapping_rows:
        return

    client = bigquery.Client(project=project_id)
    table_ref = f"{project_id}.{BQ_DATASET}.{BQ_TABLE}"

    schema = [
        bigquery.SchemaField("video_id", "STRING"),
        bigquery.SchemaField("segment_uri", "STRING"),
        bigquery.SchemaField("segment_index", "INT64"),
        bigquery.SchemaField("start_seconds", "INT64"),
        bigquery.SchemaField("end_seconds", "INT64"),
        bigquery.SchemaField("title", "STRING"),
        bigquery.SchemaField("year", "INT64"),
        bigquery.SchemaField("source_url", "STRING"),
        bigquery.SchemaField("license", "STRING"),
        bigquery.SchemaField("duration_total_seconds", "INT64"),
    ]

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )

    job = client.load_table_from_json(mapping_rows, table_ref, job_config=job_config)
    job.result()
    logger.info(f"Loaded {len(mapping_rows)} segment mapping rows to {table_ref}")


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def process_video(
    video_id: str,
    manifest_entry: dict[str, Any],
    bucket_name: str,
    local_dir: Optional[Path],
    dry_run: bool,
) -> list[dict[str, Any]]:
    """Process a single video: download, split, upload segments.

    Returns list of segment mapping rows.
    """
    title = manifest_entry.get("title", video_id)
    year = manifest_entry.get("year")

    if dry_run:
        logger.info(f"[DRY RUN] Would segment: {title} ({year or '?'})")
        return []

    with tempfile.TemporaryDirectory(prefix="video_seg_") as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Get the video file
        if local_dir:
            video_path = local_dir / f"{video_id}.mp4"
            if not video_path.exists():
                logger.warning(f"Local file not found: {video_path}")
                return []
        else:
            video_path = tmpdir_path / f"{video_id}.mp4"
            gcs_source = f"raw/{video_id}.mp4"
            logger.info(f"Downloading gs://{bucket_name}/{gcs_source}")
            if not download_from_gcs(bucket_name, gcs_source, video_path):
                return []

        # Get duration
        duration = get_video_duration(video_path)
        logger.info(f"Duration: {duration:.1f}s ({duration/60:.1f} min)")

        # Split
        segments_dir = tmpdir_path / "segments"
        logger.info(f"Splitting into {SEGMENT_DURATION}s segments...")
        segments = split_video(video_path, segments_dir)

        if not segments:
            logger.error(f"No segments produced for {video_id}")
            return []

        logger.info(f"Produced {len(segments)} segments")

        # Upload segments and build mapping
        mapping_rows = []
        for i, seg_path in enumerate(segments):
            gcs_path = f"segments/{video_id}/seg_{i:03d}.mp4"
            segment_uri = f"gs://{bucket_name}/{gcs_path}"

            logger.info(f"  Uploading segment {i}: {gcs_path}")
            if not upload_to_gcs(bucket_name, seg_path, gcs_path):
                continue

            start_seconds = i * SEGMENT_DURATION
            end_seconds = min((i + 1) * SEGMENT_DURATION, int(duration))

            mapping_rows.append({
                "video_id": video_id,
                "segment_uri": segment_uri,
                "segment_index": i,
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
                "title": title,
                "year": year,
                "source_url": manifest_entry.get("source_url", ""),
                "license": manifest_entry.get("license", "Public Domain"),
                "duration_total_seconds": int(duration),
            })

        return mapping_rows


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def show_status() -> None:
    """Display segmentation status."""
    checkpoint = load_checkpoint() if SEGMENT_CHECKPOINT_FILE.exists() else {
        "completed_ids": [], "started_at": "N/A", "last_updated": "N/A",
    }

    print(f"\n{'='*50}")
    print("Video Segmentation Status")
    print(f"{'='*50}")
    print(f"Videos segmented: {len(checkpoint.get('completed_ids', []))}")
    print(f"Started:          {checkpoint.get('started_at', 'N/A')}")
    print(f"Last updated:     {checkpoint.get('last_updated', 'N/A')}")

    if MANIFEST_FILE.exists():
        with open(MANIFEST_FILE, "r") as f:
            manifest = json.load(f)
        print(f"Manifest entries: {len(manifest)}")
        remaining = len(manifest) - len(checkpoint.get("completed_ids", []))
        print(f"Remaining:        {remaining}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Split videos into 2-minute segments for BQ embedding generation"
    )
    parser.add_argument(
        "--project", type=str,
        help="GCP project ID (overrides GCP_PROJECT_ID env var)",
    )
    parser.add_argument(
        "--video-id", type=str, nargs="+",
        help="Process specific video(s) by ID (space-separated)",
    )
    parser.add_argument(
        "--local-dir", type=Path,
        help="Read videos from local directory instead of GCS",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be processed without doing it",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show segmentation status and exit",
    )
    parser.add_argument(
        "--skip-bq-load", action="store_true",
        help="Skip loading segment mapping to BigQuery",
    )
    args = parser.parse_args()

    if args.status:
        show_status()
        sys.exit(0)

    check_ffmpeg()

    # Load config
    load_dotenv()
    project_id = args.project or os.getenv("GCP_PROJECT_ID")
    if not project_id and not args.dry_run:
        print(
            "Error: --project or GCP_PROJECT_ID env var required (unless --dry-run)",
            file=sys.stderr,
        )
        sys.exit(1)

    bucket_name = f"{project_id}{BUCKET_SUFFIX}" if project_id else "DRY-RUN-BUCKET"

    # Load manifest
    if not MANIFEST_FILE.exists():
        logger.error(
            f"Manifest not found: {MANIFEST_FILE}\n"
            f"Run source_archive_videos.py first to build it."
        )
        sys.exit(1)

    with open(MANIFEST_FILE, "r") as f:
        manifest = json.load(f)

    # Build lookup by video_id
    manifest_lookup = {entry["video_id"]: entry for entry in manifest}

    # Determine which videos to process
    if args.video_id:
        video_ids = args.video_id
        for vid in video_ids:
            if vid not in manifest_lookup:
                logger.error(f"Video ID '{vid}' not found in manifest")
                sys.exit(1)
    else:
        video_ids = [entry["video_id"] for entry in manifest]

    # Load checkpoint
    checkpoint = load_checkpoint()
    completed = set(checkpoint.get("completed_ids", []))

    logger.info(f"Project:  {project_id}")
    logger.info(f"Bucket:   gs://{bucket_name}/")
    logger.info(f"Videos:   {len(video_ids)} to process, {len(completed)} already done")
    logger.info(f"Mode:     {'DRY RUN' if args.dry_run else 'LIVE'}")
    if args.local_dir:
        logger.info(f"Source:   local ({args.local_dir})")

    all_mapping_rows: list[dict[str, Any]] = []

    try:
        for video_id in tqdm(video_ids, desc="Segmenting", unit="video"):
            if video_id in completed:
                logger.debug(f"Already segmented: {video_id}")
                continue

            entry = manifest_lookup[video_id]
            logger.info(f"\nProcessing: {entry['title']} ({entry.get('year', '?')})")

            mapping_rows = process_video(
                video_id=video_id,
                manifest_entry=entry,
                bucket_name=bucket_name,
                local_dir=args.local_dir,
                dry_run=args.dry_run,
            )

            if mapping_rows:
                all_mapping_rows.extend(mapping_rows)
                completed.add(video_id)
                checkpoint["completed_ids"] = list(completed)
                save_checkpoint(checkpoint)

                logger.info(
                    f"Segmented {entry['title']}: "
                    f"{len(mapping_rows)} segments"
                )

    except KeyboardInterrupt:
        logger.warning("\nInterrupted. Progress saved. Run again to resume.")
        save_checkpoint(checkpoint)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        save_checkpoint(checkpoint)
        sys.exit(1)

    # Load mapping to BigQuery
    if all_mapping_rows and not args.dry_run and not args.skip_bq_load:
        logger.info(f"\nLoading {len(all_mapping_rows)} segment mappings to BigQuery...")
        try:
            load_segment_mapping_to_bq(project_id, all_mapping_rows)
        except Exception as e:
            logger.error(f"BQ load failed: {e}", exc_info=True)
            logger.info("Segment files are in GCS. You can retry BQ load later.")

    # Summary
    print(f"\n{'='*60}")
    print(f"{'DRY RUN ' if args.dry_run else ''}COMPLETE")
    print(f"{'='*60}")
    print(f"Videos processed:  {len(completed)}")
    print(f"Segments created:  {len(all_mapping_rows)}")
    if not args.dry_run:
        print(f"Segments in GCS:   gs://{bucket_name}/segments/")
        if not args.skip_bq_load:
            print(f"Mapping in BQ:     {project_id}.{BQ_DATASET}.{BQ_TABLE}")


if __name__ == "__main__":
    main()
