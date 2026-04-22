"""Archive.org API router — search and ingest public domain videos."""

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks

from services.archive import search_archive, get_item_details, ingest_video

router = APIRouter()


@router.get("/api/archive/search")
def search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=50),
):
    """Search Archive.org for public domain videos."""
    return search_archive(query=q, limit=limit)


@router.get("/api/archive/{identifier}")
def details(identifier: str):
    """Get details for a specific Archive.org item."""
    item = get_item_details(identifier)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found or no MP4 available")
    return item


@router.post("/api/archive/{identifier}/ingest")
def ingest(identifier: str, background_tasks: BackgroundTasks):
    """Ingest a video from Archive.org into the library.

    Downloads the MP4 and uploads to GCS with metadata.
    The Cloud Function handles segmentation automatically.
    """
    item = get_item_details(identifier)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found or no MP4 available")

    # Run ingestion in background so the API responds immediately
    background_tasks.add_task(ingest_video, item)

    return {
        "status": "ingesting",
        "video_id": item["video_id"],
        "title": item["title"],
        "message": "Video is being downloaded and will appear in the library shortly.",
    }
