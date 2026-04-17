"""BigQuery service for vector search queries."""

import time
from typing import Any

from google.cloud import bigquery

PROJECT_ID = "gcloud-tech-showcase"
DATASET = "video_vector_search"
EMBEDDING_MODEL = f"{PROJECT_ID}.{DATASET}.multimodal_embedding_model"
GOLD_TABLE = f"{PROJECT_ID}.{DATASET}.gold_searchable_videos"

_client: bigquery.Client | None = None


def _get_client() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=PROJECT_ID)
    return _client


def search_videos(query: str, limit: int = 20) -> dict[str, Any]:
    """Run vector search and return results grouped by parent video."""
    client = _get_client()

    sql = """
    WITH segment_matches AS (
      SELECT
        base.video_id,
        base.title,
        base.year,
        base.segment_index,
        base.start_seconds,
        base.end_seconds,
        base.source_url,
        base.duration_total_seconds,
        base.category,
        base.mood,
        base.color_mode,
        base.style,
        base.ai_description,
        base.content_warnings,
        distance
      FROM VECTOR_SEARCH(
        TABLE `{gold_table}`, 'embedding',
        (
          SELECT embedding
          FROM AI.GENERATE_EMBEDDING(
            MODEL `{model}`,
            (SELECT @query_text AS content)
          )
        ),
        top_k => @top_k,
        distance_type => 'COSINE'
      )
    )
    SELECT
      video_id,
      ANY_VALUE(title) AS title,
      ANY_VALUE(year) AS year,
      ANY_VALUE(source_url) AS source_url,
      ANY_VALUE(duration_total_seconds) AS duration_total_seconds,
      ANY_VALUE(category) AS category,
      ANY_VALUE(mood) AS mood,
      ANY_VALUE(color_mode) AS color_mode,
      ANY_VALUE(style) AS style,
      ANY_VALUE(ai_description) AS ai_description,
      ANY_VALUE(CASE WHEN ARRAY_LENGTH(content_warnings) > 0 THEN 'has warnings' ELSE 'no warnings' END) AS content_warnings_status,
      ROUND(MIN(distance), 4) AS best_distance,
      COUNT(*) AS matching_intervals,
      ARRAY_AGG(
        STRUCT(
          segment_index,
          start_seconds,
          end_seconds,
          ROUND(distance, 4) AS distance
        )
        ORDER BY distance
        LIMIT 5
      ) AS top_segments
    FROM segment_matches
    GROUP BY video_id
    ORDER BY best_distance ASC
    LIMIT @result_limit
    """.format(gold_table=GOLD_TABLE, model=EMBEDDING_MODEL)

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("query_text", "STRING", query),
            bigquery.ScalarQueryParameter("top_k", "INT64", limit * 10),
            bigquery.ScalarQueryParameter("result_limit", "INT64", limit),
        ]
    )

    start = time.time()
    results = client.query(sql, job_config=job_config).result()
    elapsed_ms = int((time.time() - start) * 1000)

    videos = []
    for row in results:
        best_dist = float(row.best_distance)
        # Cosine distance ranges 0-2; convert to 0-100% similarity
        relevance_pct = round((1 - best_dist / 2) * 100, 1)

        segments = []
        for seg in row.top_segments:
            segments.append({
                "segment_index": seg["segment_index"],
                "start_seconds": seg["start_seconds"],
                "end_seconds": seg["end_seconds"],
                "distance": float(seg["distance"]),
            })

        videos.append({
            "video_id": row.video_id,
            "title": row.title,
            "year": row.year,
            "source_url": row.source_url,
            "duration_total_seconds": row.duration_total_seconds,
            "category": row.category,
            "mood": row.mood,
            "color_mode": row.color_mode,
            "style": row.style,
            "ai_description": row.ai_description,
            "content_warnings": row.content_warnings_status,
            "thumbnail_url": f"/api/videos/{row.video_id}/thumbnail",
            "best_distance": best_dist,
            "relevance_pct": relevance_pct,
            "matching_intervals": row.matching_intervals,
            "top_segments": segments,
        })

    return {
        "query": query,
        "results": videos,
        "total_results": len(videos),
        "search_time_ms": elapsed_ms,
    }


def find_similar(video_id: str, limit: int = 10) -> dict[str, Any]:
    """Find videos similar to a given video using its embedding."""
    client = _get_client()

    sql = """
    WITH seed_embedding AS (
      SELECT embedding, video_id AS seed_id
      FROM `{gold_table}`
      WHERE video_id = @video_id
        AND segment_index = 0
      LIMIT 1
    ),
    segment_matches AS (
      SELECT
        base.video_id,
        base.title,
        base.year,
        base.segment_index,
        base.start_seconds,
        base.end_seconds,
        base.source_url,
        base.duration_total_seconds,
        base.category,
        base.mood,
        base.color_mode,
        base.style,
        base.ai_description,
        base.content_warnings,
        distance
      FROM VECTOR_SEARCH(
        (SELECT * FROM `{gold_table}` WHERE video_id != @video_id),
        'embedding',
        (SELECT embedding FROM seed_embedding),
        top_k => @top_k,
        distance_type => 'COSINE'
      )
    )
    SELECT
      video_id,
      ANY_VALUE(title) AS title,
      ANY_VALUE(year) AS year,
      ANY_VALUE(source_url) AS source_url,
      ANY_VALUE(duration_total_seconds) AS duration_total_seconds,
      ANY_VALUE(category) AS category,
      ANY_VALUE(mood) AS mood,
      ANY_VALUE(color_mode) AS color_mode,
      ANY_VALUE(style) AS style,
      ANY_VALUE(ai_description) AS ai_description,
      ANY_VALUE(CASE WHEN ARRAY_LENGTH(content_warnings) > 0 THEN 'has warnings' ELSE 'no warnings' END) AS content_warnings_status,
      ROUND(MIN(distance), 4) AS best_distance,
      COUNT(*) AS matching_intervals,
      ARRAY_AGG(
        STRUCT(segment_index, start_seconds, end_seconds, ROUND(distance, 4) AS distance)
        ORDER BY distance LIMIT 5
      ) AS top_segments
    FROM segment_matches
    GROUP BY video_id
    ORDER BY best_distance ASC
    LIMIT @result_limit
    """.format(gold_table=GOLD_TABLE)

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("video_id", "STRING", video_id),
            bigquery.ScalarQueryParameter("top_k", "INT64", limit * 10),
            bigquery.ScalarQueryParameter("result_limit", "INT64", limit),
        ]
    )

    start = time.time()
    results = client.query(sql, job_config=job_config).result()
    elapsed_ms = int((time.time() - start) * 1000)

    videos = []
    for row in results:
        best_dist = float(row.best_distance)
        relevance_pct = round((1 - best_dist / 2) * 100, 1)

        segments = []
        for seg in row.top_segments:
            segments.append({
                "segment_index": seg["segment_index"],
                "start_seconds": seg["start_seconds"],
                "end_seconds": seg["end_seconds"],
                "distance": float(seg["distance"]),
            })

        videos.append({
            "video_id": row.video_id,
            "title": row.title,
            "year": row.year,
            "source_url": row.source_url,
            "duration_total_seconds": row.duration_total_seconds,
            "category": row.category,
            "mood": row.mood,
            "color_mode": row.color_mode,
            "style": row.style,
            "ai_description": row.ai_description,
            "content_warnings": row.content_warnings_status,
            "thumbnail_url": f"/api/videos/{row.video_id}/thumbnail",
            "best_distance": best_dist,
            "relevance_pct": relevance_pct,
            "matching_intervals": row.matching_intervals,
            "top_segments": segments,
        })

    return {
        "source_video_id": video_id,
        "results": videos,
        "total_results": len(videos),
        "search_time_ms": elapsed_ms,
    }


def get_library_stats() -> dict[str, Any]:
    """Get collection overview stats."""
    client = _get_client()

    sql = f"""
    WITH video_stats AS (
      SELECT
        video_id,
        ANY_VALUE(duration_total_seconds) AS duration,
        ANY_VALUE(year) AS year,
        ANY_VALUE(category) AS category
      FROM `{GOLD_TABLE}`
      GROUP BY video_id
    )
    SELECT
      COUNT(*) AS total_videos,
      COALESCE(SUM(duration), 0) AS total_duration_seconds,
      MIN(year) AS earliest_year,
      MAX(year) AS latest_year,
      COUNT(DISTINCT category) AS total_categories
    FROM video_stats
    """
    row = next(client.query(sql).result())

    # Get filter dimensions from gold table (already normalized)
    filters: dict[str, list] = {}
    filter_fields = ["category", "mood", "color_mode", "style"]
    for field in filter_fields:
        try:
            sql = f"""
            SELECT {field} AS value, COUNT(DISTINCT video_id) AS count
            FROM `{GOLD_TABLE}`
            WHERE {field} IS NOT NULL
            GROUP BY {field}
            ORDER BY count DESC
            """
            filters[field] = [
                {"name": r.value, "count": r.count}
                for r in client.query(sql).result()
            ]
        except Exception:
            filters[field] = []

    total_minutes = int(row.total_duration_seconds / 60) if row.total_duration_seconds else 0
    total_hours = round(total_minutes / 60, 1)

    # Count videos with/without content warnings
    warnings_sql = f"""
    SELECT
      CASE WHEN ARRAY_LENGTH(content_warnings) > 0 THEN 'has warnings' ELSE 'no warnings' END AS value,
      COUNT(DISTINCT video_id) AS count
    FROM `{GOLD_TABLE}`
    GROUP BY value
    """
    try:
        filters["content_warnings"] = [
            {"name": r.value, "count": r.count}
            for r in client.query(warnings_sql).result()
        ]
    except Exception:
        filters["content_warnings"] = []

    return {
        "total_videos": row.total_videos,
        "total_duration_minutes": total_minutes,
        "total_duration_hours": total_hours,
        "earliest_year": row.earliest_year,
        "latest_year": row.latest_year,
        "total_categories": row.total_categories,
        "categories": filters.get("category", []),
        "filters": filters,
    }


def get_video_details(video_id: str) -> dict[str, Any] | None:
    """Get full AI-generated metadata for a single video."""
    client = _get_client()

    sql = f"""
    SELECT
      video_id,
      ANY_VALUE(title) AS title,
      ANY_VALUE(year) AS year,
      ANY_VALUE(source_url) AS source_url,
      ANY_VALUE(duration_total_seconds) AS duration_total_seconds,
      ANY_VALUE(category) AS category,
      ANY_VALUE(mood) AS mood,
      ANY_VALUE(color_mode) AS color_mode,
      ANY_VALUE(style) AS style,
      ANY_VALUE(ai_description) AS ai_description,
      ANY_VALUE(themes) AS themes,
      ANY_VALUE(characters) AS characters,
      ANY_VALUE(language) AS language,
      ANY_VALUE(has_dialogue) AS has_dialogue,
      ANY_VALUE(has_music) AS has_music,
      ANY_VALUE(target_audience) AS target_audience,
      ANY_VALUE(setting) AS setting,
      ANY_VALUE(pacing) AS pacing,
      ANY_VALUE(content_warnings) AS content_warnings
    FROM `{GOLD_TABLE}`
    WHERE video_id = @video_id
    GROUP BY video_id
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("video_id", "STRING", video_id),
        ]
    )

    rows = list(client.query(sql, job_config=job_config).result())
    if not rows:
        return None

    row = rows[0]
    return {
        "video_id": row.video_id,
        "title": row.title,
        "year": row.year,
        "source_url": row.source_url,
        "duration_total_seconds": row.duration_total_seconds,
        "category": row.category,
        "mood": row.mood,
        "color_mode": row.color_mode,
        "style": row.style,
        "ai_description": row.ai_description,
        "themes": list(row.themes) if row.themes else [],
        "characters": list(row.characters) if row.characters else [],
        "language": row.language,
        "has_dialogue": row.has_dialogue,
        "has_music": row.has_music,
        "target_audience": row.target_audience,
        "setting": row.setting,
        "pacing": row.pacing,
        "content_warnings": list(row.content_warnings) if row.content_warnings else [],
        "thumbnail_url": f"/api/videos/{row.video_id}/thumbnail",
    }


def list_videos() -> list[dict[str, Any]]:
    """List all unique videos in the library with metadata."""
    client = _get_client()

    sql = f"""
    SELECT
      video_id,
      ANY_VALUE(title) AS title,
      ANY_VALUE(year) AS year,
      ANY_VALUE(source_url) AS source_url,
      ANY_VALUE(duration_total_seconds) AS duration_total_seconds,
      ANY_VALUE(category) AS category,
      ANY_VALUE(mood) AS mood,
      ANY_VALUE(color_mode) AS color_mode,
      ANY_VALUE(style) AS style,
      ANY_VALUE(ai_description) AS ai_description,
      ANY_VALUE(CASE WHEN ARRAY_LENGTH(content_warnings) > 0 THEN 'has warnings' ELSE 'no warnings' END) AS content_warnings_status
    FROM `{GOLD_TABLE}`
    GROUP BY video_id
    ORDER BY title
    """

    results = client.query(sql).result()

    return [
        {
            "video_id": row.video_id,
            "title": row.title,
            "year": row.year,
            "source_url": row.source_url,
            "duration_total_seconds": row.duration_total_seconds,
            "category": row.category,
            "mood": row.mood,
            "color_mode": row.color_mode,
            "style": row.style,
            "ai_description": row.ai_description,
            "content_warnings": row.content_warnings_status,
            "thumbnail_url": f"/api/videos/{row.video_id}/thumbnail",
        }
        for row in results
    ]
