"""Search API router."""

from fastapi import APIRouter, Query

from services.bigquery import search_videos

router = APIRouter()


@router.get("/api/search")
def search(
    q: str = Query(..., min_length=1, description="Natural language search query"),
    limit: int = Query(20, ge=1, le=50, description="Max results to return"),
):
    """Search videos by natural language query using BQ Vector Search."""
    return search_videos(query=q, limit=limit)
