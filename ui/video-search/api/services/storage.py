"""GCS service for media streaming."""

import os

from google.cloud import storage

BUCKET_NAME = os.environ["GCS_BUCKET"]

_client: storage.Client | None = None


def _get_client() -> storage.Client:
    global _client
    if _client is None:
        _client = storage.Client()
    return _client


def get_thumbnail_bytes(video_id: str) -> bytes | None:
    """Download thumbnail bytes, or None if it doesn't exist."""
    client = _get_client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"thumbnails/{video_id}.jpg")

    if not blob.exists():
        return None

    return blob.download_as_bytes()


def get_segment_bytes(video_id: str, segment_index: int) -> bytes | None:
    """Download segment video bytes, or None if it doesn't exist."""
    blob_path = f"segments/{video_id}/seg_{segment_index:03d}.mp4"
    client = _get_client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_path)

    if not blob.exists():
        return None

    return blob.download_as_bytes()


def get_raw_video_bytes(video_id: str) -> bytes | None:
    """Download raw video bytes."""
    client = _get_client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"raw/{video_id}.mp4")

    if not blob.exists():
        return None

    return blob.download_as_bytes()


def segment_exists(video_id: str, segment_index: int) -> bool:
    """Check if a segment exists in GCS."""
    blob_path = f"segments/{video_id}/seg_{segment_index:03d}.mp4"
    client = _get_client()
    bucket = client.bucket(BUCKET_NAME)
    return bucket.blob(blob_path).exists()
