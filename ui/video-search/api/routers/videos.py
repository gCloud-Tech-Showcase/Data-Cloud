"""Videos API router — library listing, thumbnails, and playback."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from services.bigquery import list_videos
from services.storage import get_thumbnail_url, get_segment_play_url

router = APIRouter()


@router.get("/api/videos")
async def videos():
    """List all videos in the library."""
    return {"videos": list_videos()}


@router.get("/api/videos/{video_id}/thumbnail")
async def thumbnail(video_id: str):
    """Redirect to signed URL for video thumbnail."""
    url = get_thumbnail_url(video_id)
    if not url:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return RedirectResponse(url=url)


@router.get("/api/videos/{video_id}/segments/{segment_index}/play")
async def play_segment(video_id: str, segment_index: int):
    """Get signed URL for video segment playback."""
    url = get_segment_play_url(video_id, segment_index)
    if not url:
        raise HTTPException(status_code=404, detail="Segment not found")
    return {"video_id": video_id, "segment_index": segment_index, "url": url}
