"""Archive.org service — search, download, and embed public domain videos."""

import logging
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

import requests
from google.cloud import bigquery, storage

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

    logger.info(f"Upload complete: {video_id}. Waiting for Cloud Function to segment...")

    # Wait for Cloud Function to produce segments
    _wait_for_segments(video_id)

    # Generate embeddings for the new segments
    _generate_embeddings(video_id)

    logger.info(f"Ingestion complete: {video_id} is now searchable.")


def _wait_for_segments(video_id: str, timeout: int = 120, poll_interval: int = 10) -> bool:
    """Poll GCS until segments appear for a video."""
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    deadline = time.time() + timeout

    while time.time() < deadline:
        blobs = list(bucket.list_blobs(prefix=f"segments/{video_id}/", max_results=1))
        if blobs:
            # Also check for metadata CSV
            csv_blob = bucket.blob(f"manifests/metadata/{video_id}.csv")
            if csv_blob.exists():
                logger.info(f"Segments and metadata ready for {video_id}")
                return True
        logger.info(f"Waiting for segments... ({int(deadline - time.time())}s remaining)")
        time.sleep(poll_interval)

    logger.warning(f"Timed out waiting for segments for {video_id}")
    return False


def _generate_embeddings(video_id: str) -> None:
    """Generate embeddings for a video's segments and insert into BQ tables."""
    client = bigquery.Client(project="gcloud-tech-showcase")

    # Refresh object table cache so new segments are visible
    logger.info("Refreshing metadata cache...")
    client.query(
        "CALL BQ.REFRESH_EXTERNAL_METADATA_CACHE('video_vector_search.bronze_video_segments')"
    ).result()

    # Generate embeddings for this video's segments only and insert into silver table
    logger.info(f"Generating embeddings for {video_id}...")
    embed_sql = """
    INSERT INTO `video_vector_search.silver_segment_embeddings`
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
      MODEL `video_vector_search.multimodal_embedding_model`,
      (SELECT * FROM `video_vector_search.bronze_video_segments`
       WHERE uri LIKE @uri_pattern)
    )
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "uri_pattern", "STRING", f"%/segments/{video_id}/%"
            ),
        ]
    )

    client.query(embed_sql, job_config=job_config).result()
    logger.info(f"Embeddings generated for {video_id}")

    # Rebuild gold table (full rebuild since it's a simple join)
    logger.info(f"Rebuilding gold table...")
    gold_sql = """
    CREATE OR REPLACE TABLE `video_vector_search.gold_searchable_videos` AS
    SELECT
      e.segment_uri,
      e.video_id,
      e.segment_index,
      m.title,
      m.year,
      m.source_url,
      m.license,
      m.duration_total_seconds,
      m.start_seconds,
      m.end_seconds,
      e.video_start_sec,
      e.video_end_sec,
      e.embedding
    FROM `video_vector_search.silver_segment_embeddings` e
    LEFT JOIN `video_vector_search.bronze_segment_mapping` m
      ON e.video_id = m.video_id
      AND e.segment_index = m.segment_index
    """
    client.query(gold_sql).result()
    logger.info(f"Gold table rebuilt")
