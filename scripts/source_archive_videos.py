#!/usr/bin/env python3
"""
Archive.org Public Domain Video Sourcer

Downloads public domain videos from Archive.org and uploads them to GCS
for the Video Vector Search demo.

Supports two modes:
- curated (default): Downloads from a curated list in video_sources.json.
  Deterministic and reproducible — use this for the demo.
- search: Discovers videos dynamically via the Archive.org API.
  Useful for expanding the collection beyond the curated list.

Usage:
    # Download from curated list (default, deterministic)
    python source_archive_videos.py --project PROJECT_ID --dry-run
    python source_archive_videos.py --project PROJECT_ID
    python source_archive_videos.py --project PROJECT_ID --limit 10

    # Discover and download via Archive.org search
    python source_archive_videos.py --project PROJECT_ID --source search --limit 20

    # Check progress
    python source_archive_videos.py --status
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests
from dotenv import load_dotenv
from google.cloud import storage
from tqdm import tqdm

# Configuration
SCRIPT_DIR = Path(__file__).parent
SOURCES_FILE = SCRIPT_DIR / "video_sources.json"
CHECKPOINT_FILE = SCRIPT_DIR / "video_checkpoint.json"
MANIFEST_FILE = SCRIPT_DIR / "video_manifest.json"
LOG_FILE = SCRIPT_DIR / "video_source.log"
STAGING_DIR = SCRIPT_DIR / "video_staging"
RATE_LIMIT_DELAY = 2  # seconds between downloads
GCS_PREFIX = "raw"
BUCKET_SUFFIX = "-video-search"

# Archive.org API
ARCHIVE_SEARCH_URL = "https://archive.org/advancedsearch.php"
ARCHIVE_METADATA_URL = "https://archive.org/metadata"
ARCHIVE_DOWNLOAD_URL = "https://archive.org/download"

# Search mode collection targets
SEARCH_TARGETS = [
    {
        "name": "cartoons",
        "query": (
            "collection:animationandcartoons "
            "AND mediatype:movies "
            "AND licenseurl:*publicdomain*"
        ),
        "target_count": 70,
        "category": "cartoon",
    },
    {
        "name": "prelinger",
        "query": (
            "collection:prelinger "
            "AND mediatype:movies "
            "AND licenseurl:*publicdomain*"
        ),
        "target_count": 30,
        "category": "educational",
    },
]

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
# Utilities
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    """Convert a title to a URL/filename-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text[:80].strip("-")


def load_checkpoint() -> dict[str, Any]:
    """Load checkpoint from file if it exists."""
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, "r") as f:
                checkpoint = json.load(f)
                logger.info(
                    f"Loaded checkpoint: {checkpoint['videos_downloaded']} videos downloaded"
                )
                return checkpoint
        except json.JSONDecodeError:
            backup = f"{CHECKPOINT_FILE}.corrupted"
            CHECKPOINT_FILE.rename(backup)
            logger.warning(f"Corrupted checkpoint backed up to {backup}")

    return {
        "videos_downloaded": 0,
        "downloaded_ids": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": None,
    }


def save_checkpoint(checkpoint: dict[str, Any]) -> None:
    """Save checkpoint to file."""
    checkpoint["last_updated"] = datetime.now(timezone.utc).isoformat()
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoint, f, indent=2)


def load_manifest() -> list[dict[str, Any]]:
    """Load existing manifest if present."""
    if MANIFEST_FILE.exists():
        with open(MANIFEST_FILE, "r") as f:
            return json.load(f)
    return []


def save_manifest(manifest: list[dict[str, Any]]) -> None:
    """Save manifest to file."""
    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Archive.org interaction
# ---------------------------------------------------------------------------

def search_archive(query: str, rows: int = 200) -> list[dict[str, Any]]:
    """Search Archive.org and return matching items."""
    params = {
        "q": query,
        "fl[]": [
            "identifier", "title", "year", "description",
            "licenseurl", "collection",
        ],
        "sort[]": "downloads desc",
        "rows": rows,
        "output": "json",
    }
    logger.info(f"Searching Archive.org: {query}")
    resp = requests.get(ARCHIVE_SEARCH_URL, params=params, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    results = data.get("response", {}).get("docs", [])
    total = data.get("response", {}).get("numFound", 0)
    logger.info(f"Found {total} total items, retrieved {len(results)}")
    return results


def get_item_metadata(identifier: str) -> Optional[dict[str, Any]]:
    """Fetch full metadata for an Archive.org item."""
    url = f"{ARCHIVE_METADATA_URL}/{identifier}"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch metadata for {identifier}: {e}")
        return None


def find_mp4_file(metadata: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Find the best MP4 file in an item's file list.

    Prefers the '512Kb MPEG4' derivative (small, good quality).
    Falls back to any .mp4 file, preferring smaller ones.
    """
    files = metadata.get("files", [])

    # First pass: look for 512Kb MPEG4 format
    for f in files:
        if f.get("format") == "512Kb MPEG4" and f.get("name", "").endswith(".mp4"):
            return f

    # Second pass: any MP4, prefer smallest
    mp4_files = [f for f in files if f.get("name", "").lower().endswith(".mp4")]
    if mp4_files:
        mp4_files.sort(key=lambda x: int(x.get("size", 0) or 0))
        return mp4_files[0]

    return None


# ---------------------------------------------------------------------------
# Download / Upload
# ---------------------------------------------------------------------------

def download_file(url: str, dest_path: Path) -> bool:
    """Download a file with progress bar. Returns True on success."""
    try:
        resp = requests.get(url, stream=True, timeout=300)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        with open(dest_path, "wb") as f:
            with tqdm(
                total=total, unit="B", unit_scale=True,
                desc=dest_path.name[:40], leave=False,
            ) as pbar:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    pbar.update(len(chunk))
        return True
    except requests.RequestException as e:
        logger.error(f"Download failed for {url}: {e}")
        if dest_path.exists():
            dest_path.unlink()
        return False


def upload_to_gcs(
    bucket_name: str,
    local_path: Path,
    gcs_path: str,
    custom_metadata: Optional[dict[str, str]] = None,
) -> bool:
    """Upload a file to GCS with optional custom metadata. Returns True on success."""
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_path)
        if custom_metadata:
            blob.metadata = custom_metadata
        blob.upload_from_filename(str(local_path))
        logger.debug(f"Uploaded: gs://{bucket_name}/{gcs_path}")
        return True
    except Exception as e:
        logger.error(f"GCS upload failed for {gcs_path}: {e}")
        return False


# ---------------------------------------------------------------------------
# Item processing
# ---------------------------------------------------------------------------

def _normalize_field(value: Any) -> str:
    """Normalize a metadata field that might be a list."""
    if isinstance(value, list):
        return value[0] if value else ""
    return str(value) if value else ""


def process_item(
    identifier: str,
    title: str,
    year: Optional[int],
    category: str,
    collection: str,
    bucket_name: str,
    dry_run: bool = False,
) -> Optional[dict[str, Any]]:
    """Process a single Archive.org item: fetch metadata, download, upload.

    Returns a manifest entry on success, None on failure.
    """
    # Fetch full metadata to find MP4 file
    metadata = get_item_metadata(identifier)
    if not metadata:
        return None

    mp4_file = find_mp4_file(metadata)
    if not mp4_file:
        logger.warning(f"No MP4 found for {identifier}, skipping")
        return None

    filename = mp4_file["name"]
    file_size = int(mp4_file.get("size", 0) or 0)
    download_url = f"{ARCHIVE_DOWNLOAD_URL}/{identifier}/{filename}"
    video_id = slugify(title) or slugify(identifier)

    # Determine PD reason
    pd_reason = "Explicit public domain license on Archive.org"
    if year and year < 1929:
        pd_reason = "Published before 1929 — copyright expired by statute"

    # Extract license URL from metadata if available
    meta_root = metadata.get("metadata", {})
    license_url = _normalize_field(meta_root.get("licenseurl", ""))

    entry = {
        "video_id": video_id,
        "identifier": identifier,
        "title": title,
        "year": year,
        "category": category,
        "collection": collection,
        "source_url": f"https://archive.org/details/{identifier}",
        "download_url": download_url,
        "license_url": license_url,
        "license": "Public Domain",
        "pd_reason": pd_reason,
        "file_size_bytes": file_size,
        "mp4_filename": filename,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
    }

    if dry_run:
        logger.info(
            f"[DRY RUN] Would download: {title} ({year or '?'}) "
            f"[{file_size / 1024 / 1024:.1f} MB]"
        )
        return entry

    # Download
    local_path = STAGING_DIR / f"{video_id}.mp4"
    if local_path.exists():
        logger.info(f"Already downloaded locally: {local_path.name}")
    else:
        logger.info(
            f"Downloading: {title} ({year or '?'}) [{file_size / 1024 / 1024:.1f} MB]"
        )
        if not download_file(download_url, local_path):
            return None

    # Upload to GCS with custom metadata for Cloud Function consumption
    gcs_path = f"{GCS_PREFIX}/{video_id}.mp4"
    gcs_metadata = {
        "video_id": video_id,
        "identifier": identifier,
        "title": title,
        "year": str(year) if year else "",
        "source_url": f"https://archive.org/details/{identifier}",
        "license": "Public Domain",
    }
    logger.info(f"Uploading to gs://{bucket_name}/{gcs_path}")
    if not upload_to_gcs(bucket_name, local_path, gcs_path, custom_metadata=gcs_metadata):
        return None

    # Clean up local file to save disk space
    local_path.unlink(missing_ok=True)

    return entry


# ---------------------------------------------------------------------------
# Source modes
# ---------------------------------------------------------------------------

def source_curated(
    bucket_name: str,
    checkpoint: dict[str, Any],
    manifest: list[dict[str, Any]],
    limit: Optional[int],
    dry_run: bool,
) -> int:
    """Download videos from the curated video_sources.json list."""
    if not SOURCES_FILE.exists():
        logger.error(f"Curated sources file not found: {SOURCES_FILE}")
        sys.exit(1)

    with open(SOURCES_FILE, "r") as f:
        sources = json.load(f)

    logger.info(f"Curated source list: {len(sources)} videos")

    downloaded_ids = set(checkpoint.get("downloaded_ids", []))
    total_downloaded = checkpoint["videos_downloaded"]
    effective_limit = limit or len(sources)

    for source in sources:
        if total_downloaded >= effective_limit:
            logger.info(f"Limit of {effective_limit} reached, stopping")
            break

        identifier = source["identifier"]
        if identifier in downloaded_ids:
            logger.debug(f"Already processed: {identifier}")
            continue

        entry = process_item(
            identifier=identifier,
            title=source["title"],
            year=source.get("year"),
            category=source.get("category", "unknown"),
            collection=source.get("collection", "unknown"),
            bucket_name=bucket_name,
            dry_run=dry_run,
        )

        if entry:
            manifest.append(entry)
            downloaded_ids.add(identifier)
            total_downloaded += 1

            checkpoint["videos_downloaded"] = total_downloaded
            checkpoint["downloaded_ids"] = list(downloaded_ids)
            save_checkpoint(checkpoint)
            save_manifest(manifest)

            logger.info(
                f"[{total_downloaded}/{effective_limit}] "
                f"{entry['title']} ({entry.get('year', '?')})"
            )

        if not dry_run:
            time.sleep(RATE_LIMIT_DELAY)

    return total_downloaded


def source_search(
    bucket_name: str,
    checkpoint: dict[str, Any],
    manifest: list[dict[str, Any]],
    limit: Optional[int],
    dry_run: bool,
) -> int:
    """Discover and download videos via Archive.org search API."""
    downloaded_ids = set(checkpoint.get("downloaded_ids", []))
    total_downloaded = checkpoint["videos_downloaded"]
    global_limit = limit or sum(t["target_count"] for t in SEARCH_TARGETS)

    for target in SEARCH_TARGETS:
        if total_downloaded >= global_limit:
            break

        collection_name = target["name"]
        category = target["category"]
        target_count = min(
            target["target_count"],
            global_limit - total_downloaded,
        )

        logger.info(f"\n{'='*60}")
        logger.info(f"Collection: {collection_name} (target: {target_count})")
        logger.info(f"{'='*60}")

        items = search_archive(target["query"], rows=min(target_count * 3, 500))

        collection_downloaded = 0
        for item in items:
            if collection_downloaded >= target_count:
                break
            if total_downloaded >= global_limit:
                break

            identifier = item["identifier"]
            if identifier in downloaded_ids:
                continue

            year_raw = item.get("year")
            if isinstance(year_raw, list):
                year_raw = year_raw[0] if year_raw else None
            try:
                year = int(year_raw) if year_raw else None
            except (ValueError, TypeError):
                year = None

            coll = item.get("collection", "")
            if isinstance(coll, list):
                coll = ", ".join(coll)

            entry = process_item(
                identifier=identifier,
                title=item.get("title", identifier),
                year=year,
                category=category,
                collection=coll,
                bucket_name=bucket_name,
                dry_run=dry_run,
            )

            if entry:
                manifest.append(entry)
                downloaded_ids.add(identifier)
                total_downloaded += 1
                collection_downloaded += 1

                checkpoint["videos_downloaded"] = total_downloaded
                checkpoint["downloaded_ids"] = list(downloaded_ids)
                save_checkpoint(checkpoint)
                save_manifest(manifest)

                logger.info(
                    f"[{total_downloaded}] {entry['title']} ({entry.get('year', '?')})"
                )

            if not dry_run:
                time.sleep(RATE_LIMIT_DELAY)

        logger.info(f"Collection {collection_name}: {collection_downloaded} processed")

    return total_downloaded


# ---------------------------------------------------------------------------
# Status display
# ---------------------------------------------------------------------------

def show_status() -> None:
    """Display current status."""
    checkpoint = load_checkpoint() if CHECKPOINT_FILE.exists() else {
        "videos_downloaded": 0, "started_at": "N/A", "last_updated": "N/A",
    }
    manifest = load_manifest()

    print(f"\n{'='*50}")
    print("Video Sourcing Status")
    print(f"{'='*50}")
    print(f"Videos downloaded: {checkpoint['videos_downloaded']}")
    print(f"Manifest entries:  {len(manifest)}")
    print(f"Started:           {checkpoint.get('started_at', 'N/A')}")
    print(f"Last updated:      {checkpoint.get('last_updated', 'N/A')}")

    if SOURCES_FILE.exists():
        with open(SOURCES_FILE, "r") as f:
            sources = json.load(f)
        print(f"Curated list size: {len(sources)}")

    if manifest:
        categories: dict[str, int] = {}
        for entry in manifest:
            cat = entry.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
        print("\nBy category:")
        for cat, count in sorted(categories.items()):
            print(f"  {cat}: {count}")

        total_size = sum(e.get("file_size_bytes", 0) for e in manifest)
        print(f"\nTotal size: {total_size / 1024 / 1024 / 1024:.2f} GB")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Source public domain videos from Archive.org for Video Vector Search demo"
    )
    parser.add_argument(
        "--project", type=str,
        help="GCP project ID (overrides GCP_PROJECT_ID env var)",
    )
    parser.add_argument(
        "--source", choices=["curated", "search"], default="curated",
        help="Source mode: 'curated' reads from video_sources.json (default, deterministic), "
             "'search' discovers videos via Archive.org API",
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Limit total videos to download (0 = all in curated list or collection targets)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be downloaded without downloading",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show current download status and exit",
    )
    args = parser.parse_args()

    if args.status:
        show_status()
        sys.exit(0)

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
    limit = args.limit if args.limit > 0 else None

    # Load state
    checkpoint = load_checkpoint()
    manifest = load_manifest()

    logger.info(f"Project: {project_id}")
    logger.info(f"Bucket:  gs://{bucket_name}/")
    logger.info(f"Source:  {args.source}")
    logger.info(f"Mode:    {'DRY RUN' if args.dry_run else 'LIVE'}")
    if limit:
        logger.info(f"Limit:   {limit}")

    try:
        if args.source == "curated":
            total = source_curated(
                bucket_name, checkpoint, manifest, limit, args.dry_run
            )
        else:
            total = source_search(
                bucket_name, checkpoint, manifest, limit, args.dry_run
            )
    except KeyboardInterrupt:
        logger.warning("\nInterrupted. Progress saved. Run again to resume.")
        save_checkpoint(checkpoint)
        save_manifest(manifest)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        save_checkpoint(checkpoint)
        save_manifest(manifest)
        sys.exit(1)

    # Upload manifest to GCS
    if not args.dry_run and manifest:
        manifest_gcs_path = "manifests/video_manifest.json"
        logger.info(f"Uploading manifest to gs://{bucket_name}/{manifest_gcs_path}")
        upload_to_gcs(bucket_name, MANIFEST_FILE, manifest_gcs_path)

    # Summary
    print(f"\n{'='*60}")
    print(f"{'DRY RUN ' if args.dry_run else ''}COMPLETE")
    print(f"{'='*60}")
    print(f"Videos processed: {total}")
    print(f"Manifest entries: {len(manifest)}")
    if not args.dry_run:
        print(f"GCS location:     gs://{bucket_name}/{GCS_PREFIX}/")
        print(f"Manifest:         gs://{bucket_name}/manifests/video_manifest.json")

    total_size = sum(e.get("file_size_bytes", 0) for e in manifest)
    print(f"Total size:       {total_size / 1024 / 1024 / 1024:.2f} GB")


if __name__ == "__main__":
    main()
