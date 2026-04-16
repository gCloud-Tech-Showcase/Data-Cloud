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
    SELECT
      COUNT(DISTINCT video_id) AS total_videos,
      COUNT(*) AS total_embeddings,
      COUNT(DISTINCT segment_index) AS avg_segments_approx,
      MIN(year) AS earliest_year,
      MAX(year) AS latest_year
    FROM `{GOLD_TABLE}`
    """
    row = next(client.query(sql).result())

    # Get per-category counts from the mapping table
    cat_sql = f"""
    SELECT
      CASE
        WHEN title LIKE '%Popeye%' THEN 'Popeye'
        WHEN title LIKE '%Betty Boop%' THEN 'Betty Boop'
        WHEN title LIKE '%Bugs Bunny%' OR title LIKE '%Merrie Melodies%' THEN 'Looney Tunes'
        WHEN title LIKE '%Superman%' THEN 'Superman'
        ELSE 'Other'
      END AS category,
      COUNT(DISTINCT video_id) AS count
    FROM `{GOLD_TABLE}`
    GROUP BY category
    ORDER BY count DESC
    """
    categories = [
        {"name": r.category, "count": r.count}
        for r in client.query(cat_sql).result()
    ]

    return {
        "total_videos": row.total_videos,
        "total_embeddings": row.total_embeddings,
        "earliest_year": row.earliest_year,
        "latest_year": row.latest_year,
        "categories": categories,
    }


def list_videos() -> list[dict[str, Any]]:
    """List all unique videos in the library with metadata."""
    client = _get_client()

    sql = f"""
    SELECT DISTINCT
      video_id,
      title,
      year,
      source_url,
      duration_total_seconds
    FROM `{GOLD_TABLE}`
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
            "thumbnail_url": f"/api/videos/{row.video_id}/thumbnail",
        }
        for row in results
    ]
