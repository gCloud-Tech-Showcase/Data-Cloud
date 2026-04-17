"""Archive.org service — search, download, and embed public domain videos."""

import logging
import re
import tempfile
from pathlib import Path
from typing import Any, Optional

import requests
from google.cloud import storage

ARCHIVE_SEARCH_URL = "https://archive.org/advancedsearch.php"
ARCHIVE_METADATA_URL = "https://archive.org/metadata"
ARCHIVE_DOWNLOAD_URL = "https://archive.org/download"
BUCKET_NAME = "gcloud-tech-showcase-video-search"

logger = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    """Convert text to a URL/filename-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text[:80].strip("-")


def search_archive(query: str, limit: int = 20) -> dict[str, Any]:
    """Search Archive.org for public domain videos across cartoon and educational collections."""
    combined_query = (
        f"({query}) "
        "AND mediatype:movies "
        "AND licenseurl:*publicdomain* "
        "AND (collection:animationandcartoons OR collection:prelinger)"
    )

    params = {
        "q": combined_query,
        "fl[]": ["identifier", "title", "year", "description", "collection"],
        "sort[]": "downloads desc",
        "rows": limit,
        "output": "json",
    }

    resp = requests.get(ARCHIVE_SEARCH_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("response", {}).get("docs", []):
        identifier = item.get("identifier", "")
        title = item.get("title", identifier)
        year = item.get("year")
        if isinstance(year, list):
            year = year[0] if year else None
        try:
            year = int(year) if year else None
        except (ValueError, TypeError):
            year = None

        collection = item.get("collection", "")
        if isinstance(collection, list):
            collection = ", ".join(collection)

        description = item.get("description", "")
        if isinstance(description, list):
            description = description[0] if description else ""
        # Truncate long descriptions
        if len(description) > 200:
            description = description[:200] + "..."

        results.append({
            "identifier": identifier,
            "title": title,
            "year": year,
            "description": description,
            "collection": collection,
            "thumbnail_url": f"https://archive.org/services/img/{identifier}",
            "source_url": f"https://archive.org/details/{identifier}",
        })

    return {
        "query": query,
        "results": results,
        "total_results": len(results),
    }


def get_item_details(identifier: str) -> Optional[dict[str, Any]]:
    """Get full details for an Archive.org item, including MP4 file info."""
    url = f"{ARCHIVE_METADATA_URL}/{identifier}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        metadata = resp.json()
    except requests.RequestException:
        return None

    # Find MP4 file
    files = metadata.get("files", [])
    mp4_file = None

    # Prefer 512Kb MPEG4
    for f in files:
        if f.get("format") == "512Kb MPEG4" and f.get("name", "").endswith(".mp4"):
            mp4_file = f
            break

    # Fall back to any MP4
    if not mp4_file:
        mp4_files = [f for f in files if f.get("name", "").lower().endswith(".mp4")]
        if mp4_files:
            mp4_files.sort(key=lambda x: int(x.get("size", 0) or 0))
            mp4_file = mp4_files[0]

    if not mp4_file:
        return None

    meta = metadata.get("metadata", {})
    title = meta.get("title", identifier)
    if isinstance(title, list):
        title = title[0] if title else identifier

    year = meta.get("year") or meta.get("date")
    if isinstance(year, list):
        year = year[0] if year else None
    try:
        year = int(str(year)[:4]) if year else None
    except (ValueError, TypeError):
        year = None

    file_size = int(mp4_file.get("size", 0) or 0)

    return {
        "identifier": identifier,
        "title": title,
        "year": year,
        "video_id": _slugify(title) or _slugify(identifier),
        "source_url": f"https://archive.org/details/{identifier}",
        "download_url": f"{ARCHIVE_DOWNLOAD_URL}/{identifier}/{mp4_file['name']}",
        "thumbnail_url": f"https://archive.org/services/img/{identifier}",
        "file_size_bytes": file_size,
        "file_size_mb": round(file_size / 1024 / 1024, 1),
        "mp4_filename": mp4_file["name"],
    }


def ingest_video(item: dict[str, Any]) -> None:
    """Download a video from Archive.org and upload to GCS.

    The Cloud Function will automatically segment it on upload.
    """
    video_id = item["video_id"]
    download_url = item["download_url"]

    logger.info(f"Ingesting {item['title']} ({video_id})")

    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = Path(tmpdir) / f"{video_id}.mp4"

        # Download
        logger.info(f"Downloading from {download_url}")
        resp = requests.get(download_url, stream=True, timeout=300)
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        # Upload to GCS with metadata
        logger.info(f"Uploading to GCS: raw/{video_id}.mp4")
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(f"raw/{video_id}.mp4")
        blob.metadata = {
            "video_id": video_id,
            "identifier": item["identifier"],
            "title": item["title"],
            "year": str(item.get("year") or ""),
            "source_url": item["source_url"],
            "license": "Public Domain",
        }
        blob.upload_from_filename(str(local_path))

    logger.info(
        f"Upload complete: {video_id}. Cloud Function will segment automatically. "
        f"Video will be searchable after the next scheduled Dataform run."
    )
