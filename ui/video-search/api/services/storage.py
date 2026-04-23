"""GCS service — signed URLs for media playback."""

import os
from datetime import timedelta

import google.auth
from google.auth.transport import requests as auth_requests
from google.cloud import storage

BUCKET_NAME = os.environ["GCS_BUCKET"]
SIGNED_URL_EXPIRY = timedelta(minutes=15)

_client: storage.Client | None = None
_signing_credentials = None
_auth_request = None


def _get_client() -> storage.Client:
    global _client
    if _client is None:
        _client = storage.Client()
    return _client


def _get_signing_credentials():
    """Get refreshed credentials for IAM signBlob API."""
    global _signing_credentials, _auth_request
    if _signing_credentials is None:
        _signing_credentials, _ = google.auth.default()
        _auth_request = auth_requests.Request()
    _signing_credentials.refresh(_auth_request)
    return _signing_credentials


def _generate_signed_url(blob_path: str) -> str | None:
    """Generate a V4 signed URL for a GCS blob, or None if it doesn't exist.

    Uses the IAM signBlob API so it works with Compute Engine credentials
    on Cloud Run (no private key needed).
    """
    client = _get_client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_path)

    if not blob.exists():
        return None

    credentials = _get_signing_credentials()
    return blob.generate_signed_url(
        version="v4",
        expiration=SIGNED_URL_EXPIRY,
        method="GET",
        service_account_email=credentials.service_account_email,
        access_token=credentials.token,
    )


def get_thumbnail_signed_url(video_id: str) -> str | None:
    """Get a signed URL for a video thumbnail."""
    return _generate_signed_url(f"thumbnails/{video_id}.jpg")


def get_segment_signed_url(video_id: str, segment_index: int) -> str | None:
    """Get a signed URL for a video segment."""
    return _generate_signed_url(f"segments/{video_id}/seg_{segment_index:03d}.mp4")


def get_video_signed_url(video_id: str) -> str | None:
    """Get a signed URL for a full raw video."""
    return _generate_signed_url(f"raw/{video_id}.mp4")


def segment_exists(video_id: str, segment_index: int) -> bool:
    """Check if a segment exists in GCS."""
    blob_path = f"segments/{video_id}/seg_{segment_index:03d}.mp4"
    client = _get_client()
    bucket = client.bucket(BUCKET_NAME)
    return bucket.blob(blob_path).exists()
