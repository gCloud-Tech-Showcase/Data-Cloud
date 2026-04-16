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
        relevance_pct = round((1 - best_dist) * 100, 1)

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
