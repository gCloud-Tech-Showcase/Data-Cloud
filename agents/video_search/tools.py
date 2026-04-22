"""Self-contained tool functions for The Archivist (Agent Engine deployment).

This module duplicates the BQ queries from ui/video-search/api/services/bigquery.py
so the agent can be deployed independently to Agent Engine without importing from
the UI's service layer.
"""

import logging
import os
import time
from typing import Any

from google.cloud import bigquery
from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# BigQuery client and config (self-contained, no external imports)
# ---------------------------------------------------------------------------

DATASET = "video_vector_search"


def _project_id() -> str:
    return os.environ["GOOGLE_CLOUD_PROJECT"]


def _gold_table() -> str:
    return f"{_project_id()}.{DATASET}.gold_searchable_videos"


def _embedding_model() -> str:
    return f"{_project_id()}.{DATASET}.multimodal_embedding_model"


_client: bigquery.Client | None = None


def _get_client() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=_project_id())
    return _client


def _row_to_video_dict(row) -> dict[str, Any]:
    """Convert a BigQuery result row (with segments) to a video dict."""
    best_dist = float(row.best_distance)
    relevance_pct = round((1 - best_dist / 2) * 100, 1)

    segments = [
        {
            "segment_index": seg["segment_index"],
            "start_seconds": seg["start_seconds"],
            "end_seconds": seg["end_seconds"],
            "distance": float(seg["distance"]),
        }
        for seg in row.top_segments
    ]

    return {
        "video_id": row.video_id,
        "title": row.title,
        "year": row.year,
        "category": row.category,
        "mood": row.mood,
        "color_mode": row.color_mode,
        "style": row.style,
        "ai_description": row.ai_description,
        "best_distance": best_dist,
        "relevance_pct": relevance_pct,
        "matching_intervals": row.matching_intervals,
        "top_segments": segments,
    }


def _append_action(tool_context: ToolContext, action: dict[str, Any]) -> None:
    """Append a UI action to the invocation-scoped state.

    In Agent Engine / Gemini Enterprise, these actions are not consumed by a
    frontend — they are simply ignored. The tool still records them for
    consistency with the embedded UI version.
    """
    actions = tool_context.state.get("actions", [])
    actions.append(action)
    tool_context.state["actions"] = actions


def _format_video_summary(video: dict[str, Any], index: int) -> str:
    """Format a single video result as a text summary line for the agent."""
    year = video.get("year") or "unknown year"
    category = video.get("category") or "uncategorized"
    relevance = video.get("relevance_pct", 0)
    duration = video.get("duration_total_seconds")
    duration_str = f", {int(duration // 60)}m{int(duration % 60)}s" if duration else ""
    return (
        f"{index}. \"{video.get('title', 'Untitled')}\" ({year}) — {category}, "
        f"{relevance}% match{duration_str} [ID: {video.get('video_id', 'unknown')}]"
    )


# ---------------------------------------------------------------------------
# UI Tools — trigger actions in the portal (harmless in Agent Engine)
# ---------------------------------------------------------------------------


def search_videos(query: str, tool_context: ToolContext) -> dict:
    """Search the video library using natural language. Use this when the user
    wants to find videos by describing content, themes, mood, or any concept.

    Args:
        query: Natural language description of what to search for.
            Examples: "adventure cartoons", "educational films about science",
            "videos with animals in nature", "dramatic black and white footage".
    """
    client = _get_client()
    gold_table = _gold_table()
    model = _embedding_model()

    sql = """
    WITH segment_matches AS (
      SELECT
        base.video_id, base.title, base.year,
        base.segment_index, base.start_seconds, base.end_seconds,
        base.duration_total_seconds, base.category, base.mood,
        base.color_mode, base.style, base.ai_description,
        base.content_warnings, distance
      FROM VECTOR_SEARCH(
        TABLE `{gold_table}`, 'embedding',
        (SELECT embedding FROM AI.GENERATE_EMBEDDING(
          MODEL `{model}`, (SELECT @query_text AS content))),
        top_k => @top_k, distance_type => 'COSINE')
    )
    SELECT video_id,
      ANY_VALUE(title) AS title, ANY_VALUE(year) AS year,
      ANY_VALUE(duration_total_seconds) AS duration_total_seconds,
      ANY_VALUE(category) AS category, ANY_VALUE(mood) AS mood,
      ANY_VALUE(color_mode) AS color_mode, ANY_VALUE(style) AS style,
      ANY_VALUE(ai_description) AS ai_description,
      ANY_VALUE(CASE WHEN ARRAY_LENGTH(content_warnings) > 0
        THEN 'has warnings' ELSE 'no warnings' END) AS content_warnings_status,
      ROUND(MIN(distance), 4) AS best_distance,
      COUNT(*) AS matching_intervals,
      ARRAY_AGG(STRUCT(segment_index, start_seconds, end_seconds,
        ROUND(distance, 4) AS distance) ORDER BY distance LIMIT 5) AS top_segments
    FROM segment_matches
    GROUP BY video_id ORDER BY best_distance ASC LIMIT @result_limit
    """.format(gold_table=gold_table, model=model)

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("query_text", "STRING", query),
            bigquery.ScalarQueryParameter("top_k", "INT64", 200),
            bigquery.ScalarQueryParameter("result_limit", "INT64", 20),
        ]
    )

    start = time.time()
    results = client.query(sql, job_config=job_config).result()
    elapsed_ms = int((time.time() - start) * 1000)

    videos = [_row_to_video_dict(row) for row in results]

    _append_action(tool_context, {"type": "search", "query": query})

    if not videos:
        return {"status": "no_results", "message": f"No videos found for '{query}'."}

    summaries = [_format_video_summary(v, i + 1) for i, v in enumerate(videos[:8])]
    return {
        "status": "success",
        "total_results": len(videos),
        "search_time_ms": elapsed_ms,
        "top_results": "\n".join(summaries),
        "message": (
            f"Found {len(videos)} videos matching '{query}' "
            f"in {elapsed_ms}ms."
        ),
    }


def apply_filters(
    category: str = "",
    mood: str = "",
    color_mode: str = "",
    style: str = "",
    *,
    tool_context: ToolContext,
) -> dict:
    """Apply filters to narrow the video library display. Only provide the
    filters you want to change — omit or leave empty any you don't need.

    Args:
        category: Filter by category (e.g. "cartoon", "educational", "documentary",
            "industrial", "newsreel", "promotional", "religious", "short film").
        mood: Filter by mood (e.g. "lighthearted", "dramatic", "inspirational",
            "informative", "nostalgic", "suspenseful", "whimsical").
        color_mode: Filter by color mode ("color" or "black and white").
        style: Filter by visual style (e.g. "animation", "live action",
            "mixed media", "stop motion").
    """
    filters = {}
    if category:
        filters["category"] = category
    if mood:
        filters["mood"] = mood
    if color_mode:
        filters["color_mode"] = color_mode
    if style:
        filters["style"] = style

    if not filters:
        return {"status": "error", "message": "Please specify at least one filter."}

    for field, value in filters.items():
        _append_action(tool_context, {"type": "apply_filter", "field": field, "value": value})

    applied = ", ".join(f"{k}={v}" for k, v in filters.items())
    return {"status": "success", "message": f"Applied filters: {applied}."}


def clear_filters(tool_context: ToolContext) -> dict:
    """Reset all active filters to show the full library. Use this when the
    user wants to start over or see everything.
    """
    _append_action(tool_context, {"type": "clear_filters"})
    return {"status": "success", "message": "All filters cleared. Showing full library."}


def get_video_details(video_id: str, tool_context: ToolContext) -> dict:
    """Get the full AI-generated metadata for a specific video. Returns all
    15 metadata fields including themes, characters, setting, pacing, and more.

    Args:
        video_id: The unique identifier of the video to inspect.
    """
    client = _get_client()
    gold_table = _gold_table()

    sql = f"""
    SELECT video_id,
      ANY_VALUE(title) AS title, ANY_VALUE(year) AS year,
      ANY_VALUE(duration_total_seconds) AS duration_total_seconds,
      ANY_VALUE(category) AS category, ANY_VALUE(mood) AS mood,
      ANY_VALUE(color_mode) AS color_mode, ANY_VALUE(style) AS style,
      ANY_VALUE(ai_description) AS ai_description,
      ANY_VALUE(themes) AS themes, ANY_VALUE(characters) AS characters,
      ANY_VALUE(language) AS language, ANY_VALUE(has_dialogue) AS has_dialogue,
      ANY_VALUE(has_music) AS has_music, ANY_VALUE(target_audience) AS target_audience,
      ANY_VALUE(setting) AS setting, ANY_VALUE(pacing) AS pacing,
      ANY_VALUE(content_warnings) AS content_warnings
    FROM `{gold_table}` WHERE video_id = @video_id GROUP BY video_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("video_id", "STRING", video_id)]
    )
    rows = list(client.query(sql, job_config=job_config).result())
    if not rows:
        return {"status": "error", "message": f"Video '{video_id}' not found."}

    _append_action(tool_context, {"type": "show_details", "video_id": video_id})

    row = rows[0]
    themes = ", ".join(list(row.themes) if row.themes else []) or "none identified"
    characters = ", ".join(list(row.characters) if row.characters else []) or "none identified"
    warnings = ", ".join(list(row.content_warnings) if row.content_warnings else []) or "none"
    duration = row.duration_total_seconds
    duration_str = f"{int(duration // 60)}m {int(duration % 60)}s" if duration else "unknown"

    return {
        "status": "success",
        "video_id": row.video_id, "title": row.title, "year": row.year,
        "duration": duration_str, "category": row.category, "mood": row.mood,
        "color_mode": row.color_mode, "style": row.style,
        "description": row.ai_description, "themes": themes,
        "characters": characters, "language": row.language,
        "has_dialogue": row.has_dialogue, "has_music": row.has_music,
        "target_audience": row.target_audience, "setting": row.setting,
        "pacing": row.pacing, "content_warnings": warnings,
        "message": f"Details for \"{row.title}\".",
    }


def find_similar(video_id: str, tool_context: ToolContext) -> dict:
    """Find videos that are visually and thematically similar to a given video.
    Uses vector similarity on multimodal embeddings.

    Args:
        video_id: The unique identifier of the video to find similar matches for.
    """
    client = _get_client()
    gold_table = _gold_table()

    sql = """
    WITH seed_embedding AS (
      SELECT embedding FROM `{gold_table}`
      WHERE video_id = @video_id AND segment_index = 0 LIMIT 1
    ),
    segment_matches AS (
      SELECT base.video_id, base.title, base.year,
        base.segment_index, base.start_seconds, base.end_seconds,
        base.duration_total_seconds, base.category, base.mood,
        base.color_mode, base.style, base.ai_description,
        base.content_warnings, distance
      FROM VECTOR_SEARCH(
        (SELECT * FROM `{gold_table}` WHERE video_id != @video_id),
        'embedding', (SELECT embedding FROM seed_embedding),
        top_k => @top_k, distance_type => 'COSINE')
    )
    SELECT video_id,
      ANY_VALUE(title) AS title, ANY_VALUE(year) AS year,
      ANY_VALUE(duration_total_seconds) AS duration_total_seconds,
      ANY_VALUE(category) AS category, ANY_VALUE(mood) AS mood,
      ANY_VALUE(color_mode) AS color_mode, ANY_VALUE(style) AS style,
      ANY_VALUE(ai_description) AS ai_description,
      ANY_VALUE(CASE WHEN ARRAY_LENGTH(content_warnings) > 0
        THEN 'has warnings' ELSE 'no warnings' END) AS content_warnings_status,
      ROUND(MIN(distance), 4) AS best_distance,
      COUNT(*) AS matching_intervals,
      ARRAY_AGG(STRUCT(segment_index, start_seconds, end_seconds,
        ROUND(distance, 4) AS distance) ORDER BY distance LIMIT 5) AS top_segments
    FROM segment_matches
    GROUP BY video_id ORDER BY best_distance ASC LIMIT @result_limit
    """.format(gold_table=gold_table)

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("video_id", "STRING", video_id),
            bigquery.ScalarQueryParameter("top_k", "INT64", 100),
            bigquery.ScalarQueryParameter("result_limit", "INT64", 10),
        ]
    )

    start = time.time()
    results = client.query(sql, job_config=job_config).result()
    elapsed_ms = int((time.time() - start) * 1000)

    videos = [_row_to_video_dict(row) for row in results]

    _append_action(tool_context, {"type": "find_similar", "video_id": video_id})

    if not videos:
        return {"status": "no_results", "message": f"No similar videos found for '{video_id}'."}

    summaries = [_format_video_summary(v, i + 1) for i, v in enumerate(videos[:8])]
    return {
        "status": "success",
        "total_results": len(videos),
        "top_results": "\n".join(summaries),
        "message": f"Found {len(videos)} similar videos.",
    }


def play_video(video_id: str, tool_context: ToolContext) -> dict:
    """Play a specific video in the video player.

    Args:
        video_id: The unique identifier of the video to play.
    """
    _append_action(tool_context, {"type": "play", "video_id": video_id})
    return {"status": "success", "message": f"Opening video player for '{video_id}'."}


def create_collection(name: str, video_ids: list[str], tool_context: ToolContext) -> dict:
    """Select a set of videos for collection export. The selected videos will
    appear in the selection bar where the user can export them as JSON or CSV
    with full AI metadata.

    Args:
        name: A descriptive name for the collection.
        video_ids: List of video IDs to include in the collection.
    """
    if not video_ids:
        return {"status": "error", "message": "Please provide at least one video ID."}

    _append_action(tool_context, {
        "type": "create_collection", "name": name, "video_ids": video_ids,
    })
    return {
        "status": "success",
        "message": f"Selected {len(video_ids)} videos for collection \"{name}\".",
    }


# ---------------------------------------------------------------------------
# Data Tools — answer questions, work in both portal and Gemini Enterprise
# ---------------------------------------------------------------------------


def get_library_stats(tool_context: ToolContext) -> dict:
    """Get an overview of the entire video library including total videos,
    duration, year range, and breakdowns by category, mood, color mode, and style.
    Use this for questions like "how many videos do we have?" or "what categories exist?"
    """
    client = _get_client()
    gold_table = _gold_table()

    sql = f"""
    WITH video_stats AS (
      SELECT video_id,
        ANY_VALUE(duration_total_seconds) AS duration,
        ANY_VALUE(year) AS year, ANY_VALUE(category) AS category
      FROM `{gold_table}` GROUP BY video_id
    )
    SELECT COUNT(*) AS total_videos,
      COALESCE(SUM(duration), 0) AS total_duration_seconds,
      MIN(year) AS earliest_year, MAX(year) AS latest_year,
      COUNT(DISTINCT category) AS total_categories
    FROM video_stats
    """
    row = next(client.query(sql).result())

    # Get category breakdowns
    filter_fields = ["category", "mood", "color_mode", "style"]
    breakdowns = {}
    for field in filter_fields:
        try:
            dim_sql = f"""
            SELECT {field} AS value, COUNT(DISTINCT video_id) AS count
            FROM `{gold_table}` WHERE {field} IS NOT NULL
            GROUP BY {field} ORDER BY count DESC
            """
            label = field.replace("_", " ").title()
            items = [f"  {r.value}: {r.count} videos" for r in client.query(dim_sql).result()]
            if items:
                breakdowns[label] = "\n".join(items)
        except Exception:
            pass

    total_hours = round(int(row.total_duration_seconds / 60) / 60, 1) if row.total_duration_seconds else 0

    return {
        "status": "success",
        "total_videos": row.total_videos,
        "total_duration_hours": total_hours,
        "earliest_year": row.earliest_year,
        "latest_year": row.latest_year,
        "total_categories": row.total_categories,
        "breakdowns": breakdowns,
        "message": (
            f"Library contains {row.total_videos} videos, "
            f"{total_hours} hours of content, "
            f"spanning {row.earliest_year}–{row.latest_year}."
        ),
    }


def query_metadata(query: str, tool_context: ToolContext) -> dict:
    """Ask an analytical question about the video metadata in BigQuery using
    the Conversational Analytics API. Use this for complex data questions that
    go beyond simple stats, such as comparisons, trends, or cross-cutting analysis.

    Examples: "What percentage of cartoons are in color?",
    "Compare the average duration of educational vs documentary videos",
    "Which decade has the most content?"

    Args:
        query: A standalone natural language question about the video data.
            Must be self-contained with all necessary context.
    """
    try:
        from google.cloud import geminidataanalytics as ca

        project_id = _project_id()
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

        client = ca.DataChatServiceClient()

        table_ref = ca.BigQueryTableReference(
            project_id=project_id,
            dataset_id=DATASET,
            table_id="gold_searchable_videos",
        )

        request = ca.QueryDataRequest(
            parent=f"projects/{project_id}/locations/{location}",
            prompt=query,
            context=ca.QueryDataContext(
                datasource_references=ca.DatasourceReferences(
                    bq=ca.BigQueryTableReferences(
                        table_references=[table_ref],
                    )
                )
            ),
            generation_options=ca.GenerationOptions(
                generate_query_result=True,
                generate_natural_language_answer=True,
            ),
        )

        response = client.query_data(request=request)

        if response.natural_language_answer:
            result = {"status": "success", "answer": response.natural_language_answer}
            if response.generated_query:
                result["sql"] = response.generated_query
            return result

        return {
            "status": "error",
            "message": "The Conversational Analytics API returned no answer. Try rephrasing.",
        }

    except ImportError:
        return {
            "status": "error",
            "message": (
                "The Conversational Analytics API (google-cloud-geminidataanalytics) "
                "is not installed. Use get_library_stats for basic questions."
            ),
        }
    except Exception:
        logger.exception("Conversational Analytics query failed")
        return {
            "status": "error",
            "message": "Conversational Analytics query failed. Try get_library_stats instead.",
        }
