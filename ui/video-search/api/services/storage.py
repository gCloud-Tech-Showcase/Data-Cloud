"""GCS service for signed URLs and media serving."""

from datetime import timedelta

from google.cloud import storage

BUCKET_NAME = "gcloud-tech-showcase-video-search"

_client: storage.Client | None = None


def _get_client() -> storage.Client:
    global _client
    if _client is None:
        _client = storage.Client()
    return _client


def generate_signed_url(blob_path: str, expiration_minutes: int = 30) -> str:
    """Generate a signed URL for a GCS object."""
    client = _get_client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_path)
    return blob.generate_signed_url(
        expiration=timedelta(minutes=expiration_minutes),
        method="GET",
    )


def get_thumbnail_url(video_id: str) -> str | None:
    """Get signed URL for a video's thumbnail, or None if it doesn't exist."""
    client = _get_client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"thumbnails/{video_id}.jpg")

    if not blob.exists():
        return None

    return blob.generate_signed_url(
        expiration=timedelta(minutes=60),
        method="GET",
    )


def get_segment_play_url(video_id: str, segment_index: int) -> str | None:
    """Get signed URL for a video segment."""
    client = _get_client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"segments/{video_id}/seg_{segment_index:03d}.mp4")

    if not blob.exists():
        return None

    return blob.generate_signed_url(
        expiration=timedelta(minutes=30),
        method="GET",
    )
