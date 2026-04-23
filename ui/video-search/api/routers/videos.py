"""Videos API router — library listing, thumbnails, and playback."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from services.bigquery import list_videos, find_similar, get_library_stats, get_video_details
from services.storage import get_thumbnail_signed_url, get_segment_signed_url, get_video_signed_url

router = APIRouter()


@router.get("/api/videos")
def videos():
    """List all videos in the library."""
    return {"videos": list_videos()}


@router.get("/api/videos/stats")
def stats():
    """Get library collection stats."""
    return get_library_stats()


@router.get("/api/videos/{video_id}/similar")
def similar(
    video_id: str,
    limit: int = Query(10, ge=1, le=50, description="Max results to return"),
):
    """Find videos similar to a given video."""
    return find_similar(video_id, limit=limit)


@router.get("/api/videos/{video_id}/details")
def video_details(video_id: str):
    """Get full AI-generated metadata for a single video."""
    details = get_video_details(video_id)
    if not details:
        raise HTTPException(status_code=404, detail="Video not found")
    return details


@router.get("/api/videos/{video_id}/thumbnail")
def thumbnail(video_id: str):
    """Redirect to signed GCS URL for video thumbnail."""
    url = get_thumbnail_signed_url(video_id)
    if not url:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return RedirectResponse(url=url, status_code=307)


@router.get("/api/videos/{video_id}/segments/{segment_index}/play")
def play_segment(video_id: str, segment_index: int):
    """Redirect to signed GCS URL for video segment playback."""
    url = get_segment_signed_url(video_id, segment_index)
    if not url:
        raise HTTPException(status_code=404, detail="Segment not found")
    return RedirectResponse(url=url, status_code=307)


@router.get("/api/videos/{video_id}/play")
def play_full(video_id: str):
    """Redirect to signed GCS URL for full video playback."""
    url = get_video_signed_url(video_id)
    if not url:
        raise HTTPException(status_code=404, detail="Video not found")
    return RedirectResponse(url=url, status_code=307)
