"""Videos API router — library listing, thumbnails, and playback."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from services.bigquery import list_videos
from services.storage import get_thumbnail_bytes, get_segment_bytes

router = APIRouter()


@router.get("/api/videos")
async def videos():
    """List all videos in the library."""
    return {"videos": list_videos()}


@router.get("/api/videos/{video_id}/thumbnail")
async def thumbnail(video_id: str):
    """Serve video thumbnail image."""
    data = get_thumbnail_bytes(video_id)
    if not data:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return Response(content=data, media_type="image/jpeg")


@router.get("/api/videos/{video_id}/segments/{segment_index}/play")
async def play_segment(video_id: str, segment_index: int):
    """Stream video segment for playback."""
    data = get_segment_bytes(video_id, segment_index)
    if not data:
        raise HTTPException(status_code=404, detail="Segment not found")
    return Response(
        content=data,
        media_type="video/mp4",
        headers={"Accept-Ranges": "bytes"},
    )
