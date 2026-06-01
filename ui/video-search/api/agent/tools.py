"""Agent tool functions for The Archivist.

Each tool is a plain Python function with typed parameters and a docstring.
ADK auto-wraps these as FunctionTool instances. The docstring is sent to the
LLM so it knows when and how to call each tool.

Tools that trigger UI actions append to tool_context.state["actions"].
The router resets this list via state_delta before each invocation and reads
it from the session after the agent finishes.
"""

import logging
import os
from typing import Any

from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)

from services.bigquery import (
    search_videos as bq_search_videos,
    find_similar as bq_find_similar,
    get_video_details as bq_get_video_details,
    get_library_stats as bq_get_library_stats,
)


def _append_action(tool_context: ToolContext, action: dict[str, Any]) -> None:
    """Append a UI action to the invocation-scoped state."""
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
# UI Tools — trigger actions in the portal
# ---------------------------------------------------------------------------


def search_videos(query: str, tool_context: ToolContext) -> dict:
    """Search the video library using natural language. Use this when the user
    wants to find videos by describing content, themes, mood, or any concept.

    Args:
        query: Natural language description of what to search for.
            Examples: "adventure cartoons", "educational films about science",
            "videos with animals in nature", "dramatic black and white footage".
    """
    result = bq_search_videos(query)
    _append_action(tool_context, {"type": "search", "query": query})

    videos = result["results"]
    if not videos:
        return {
            "status": "no_results",
            "message": f"No videos found for '{query}'.",
        }

    summaries = [_format_video_summary(v, i + 1) for i, v in enumerate(videos[:8])]
    return {
        "status": "success",
        "total_results": result["total_results"],
        "search_time_ms": result["search_time_ms"],
        "top_results": "\n".join(summaries),
        "message": (
            f"Found {result['total_results']} videos matching '{query}' "
            f"in {result['search_time_ms']}ms. The UI has been updated with results."
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
        _append_action(tool_context, {
            "type": "apply_filter",
            "field": field,
            "value": value,
        })

    applied = ", ".join(f"{k}={v}" for k, v in filters.items())
    return {
        "status": "success",
        "message": f"Applied filters: {applied}. The UI has been updated.",
    }


def clear_filters(tool_context: ToolContext) -> dict:
    """Reset all active filters to show the full library. Use this when the
    user wants to start over or see everything.
    """
    _append_action(tool_context, {"type": "clear_filters"})
    return {"status": "success", "message": "All filters cleared. Showing full library."}


def get_video_details(video_id: str, tool_context: ToolContext) -> dict:
    """Get the full AI-generated metadata for a specific video. Returns all
    15 metadata fields including themes, characters, setting, pacing, and more.
    Also opens the detail panel in the UI.

    Args:
        video_id: The unique identifier of the video to inspect.
    """
    details = bq_get_video_details(video_id)
    if not details:
        return {"status": "error", "message": f"Video '{video_id}' not found."}

    _append_action(tool_context, {"type": "show_details", "video_id": video_id})

    # Format metadata as readable text for the agent
    themes = ", ".join(details.get("themes", [])) or "none identified"
    characters = ", ".join(details.get("characters", [])) or "none identified"
    warnings = ", ".join(details.get("content_warnings", [])) or "none"
    duration = details.get("duration_total_seconds")
    duration_str = f"{int(duration // 60)}m {int(duration % 60)}s" if duration else "unknown"

    return {
        "status": "success",
        "video_id": details["video_id"],
        "title": details["title"],
        "year": details.get("year"),
        "duration": duration_str,
        "category": details.get("category"),
        "mood": details.get("mood"),
        "color_mode": details.get("color_mode"),
        "style": details.get("style"),
        "description": details.get("ai_description"),
        "themes": themes,
        "characters": characters,
        "language": details.get("language"),
        "has_dialogue": details.get("has_dialogue"),
        "has_music": details.get("has_music"),
        "target_audience": details.get("target_audience"),
        "setting": details.get("setting"),
        "pacing": details.get("pacing"),
        "content_warnings": warnings,
        "message": f"Showing details for \"{details['title']}\" in the detail panel.",
    }


def find_similar(video_id: str, tool_context: ToolContext) -> dict:
    """Find videos that are visually and thematically similar to a given video.
    Uses vector similarity on multimodal embeddings.

    Args:
        video_id: The unique identifier of the video to find similar matches for.
    """
    result = bq_find_similar(video_id)
    _append_action(tool_context, {"type": "find_similar", "video_id": video_id})

    videos = result["results"]
    if not videos:
        return {
            "status": "no_results",
            "message": f"No similar videos found for '{video_id}'.",
        }

    summaries = [_format_video_summary(v, i + 1) for i, v in enumerate(videos[:8])]
    return {
        "status": "success",
        "total_results": result["total_results"],
        "top_results": "\n".join(summaries),
        "message": (
            f"Found {result['total_results']} similar videos. "
            "The UI has been updated with results."
        ),
    }


def play_video(video_id: str, tool_context: ToolContext) -> dict:
    """Play a specific video in the video player.

    Args:
        video_id: The unique identifier of the video to play.
    """
    _append_action(tool_context, {"type": "play", "video_id": video_id})
    return {"status": "success", "message": f"Opening video player for '{video_id}'."}


def create_collection(
    name: str,
    video_ids: list[str],
    tool_context: ToolContext,
) -> dict:
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
        "type": "create_collection",
        "name": name,
        "video_ids": video_ids,
    })
    return {
        "status": "success",
        "message": (
            f"Selected {len(video_ids)} videos for collection \"{name}\". "
            "The selection bar is now visible — use it to export as JSON or CSV."
        ),
    }


# ---------------------------------------------------------------------------
# Data Tools — answer questions, work in both portal and Gemini Enterprise
# ---------------------------------------------------------------------------


def get_library_stats(tool_context: ToolContext) -> dict:
    """Get an overview of the entire video library including total videos,
    duration, year range, and breakdowns by category, mood, color mode, and style.
    Use this for questions like "how many videos do we have?" or "what categories exist?"
    """
    stats = bq_get_library_stats()

    # Format filter breakdowns as readable text
    breakdowns = {}
    for field, options in stats.get("filters", {}).items():
        if options:
            label = field.replace("_", " ").title()
            items = [f"  {o['name']}: {o['count']} videos" for o in options]
            breakdowns[label] = "\n".join(items)

    return {
        "status": "success",
        "total_videos": stats["total_videos"],
        "total_duration_hours": stats["total_duration_hours"],
        "earliest_year": stats["earliest_year"],
        "latest_year": stats["latest_year"],
        "total_categories": stats["total_categories"],
        "breakdowns": breakdowns,
        "message": (
            f"Library contains {stats['total_videos']} videos, "
            f"{stats['total_duration_hours']} hours of content, "
            f"spanning {stats['earliest_year']}–{stats['latest_year']}."
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

        project_id = os.environ["GCP_PROJECT_ID"]
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

        client = ca.DataChatServiceClient()

        table_ref = ca.BigQueryTableReference(
            project_id=project_id,
            dataset_id="video_vector_search",
            table_id="gold_searchable_videos",
        )

        # Use chat() with inline_context (stateless) instead of query_data —
        # query_data does not support BigQuery (only AlloyDB / Spanner / Cloud SQL).
        # chat() supports BigQuery and runs stateless when inline_context is set.
        #
        # Append a chart hint so CA considers emitting a visualization. The
        # Archivist's outer LLM tends to strip presentation language ("as a
        # pie chart") from the query before calling this tool, so adding it
        # here guarantees CA sees an imperative chart cue. CA still has
        # discretion to skip the chart when the result isn't chartable
        # (e.g. a single number).
        ca_query = (
            f"{query}\n\n"
            "If this question is suitable for visualization, also create a chart."
        )
        request = ca.ChatRequest(
            parent=f"projects/{project_id}/locations/{location}",
            inline_context=ca.Context(
                datasource_references=ca.DatasourceReferences(
                    bq=ca.BigQueryTableReferences(
                        table_references=[table_ref],
                    )
                ),
            ),
            messages=[
                ca.Message(user_message=ca.UserMessage(text=ca_query)),
            ],
        )

        # chat() streams a sequence of system messages. Per the proto
        # definition (geminidataanalytics_v1alpha types data_chat_service.py),
        # only TextMessage with text_type == FINAL_RESPONSE is the user-facing
        # answer; THOUGHT is the model's internal reasoning and PROGRESS is
        # informational (e.g. tool-invocation notices). We collect only
        # FINAL_RESPONSE text + the generated SQL + the optional chart spec.
        # Keep this branch in sync with agents/video_search/tools.py.
        FINAL = ca.TextMessage.TextType.FINAL_RESPONSE
        answer_parts: list[str] = []
        sql: str | None = None
        error_text: str | None = None
        chart_spec: dict | None = None
        for msg in client.chat(request=request):
            sm = msg.system_message
            if sm.text and sm.text.parts and sm.text.text_type == FINAL:
                answer_parts.extend(sm.text.parts)
            if sm.data and sm.data.generated_sql:
                sql = sm.data.generated_sql
            # Chart: only ChartMessage.result.vega_config is renderable
            # (ChartMessage.query is the planning intent, not a final spec).
            chart_msg = getattr(sm, "chart", None)
            if chart_msg and chart_msg.result and chart_msg.result.vega_config:
                # vega_config is a google.protobuf.Struct wrapped as a
                # proto-plus MapComposite (no .to_dict on the field itself).
                # Converting the parent ChartResult recursively yields a plain
                # dict where vega_config is already a JSON-serializable dict.
                result_dict = type(chart_msg.result).to_dict(chart_msg.result)
                chart_spec = result_dict.get("vega_config") or chart_spec
            if sm.error and sm.error.text:
                error_text = sm.error.text

        answer = "\n".join(p for p in answer_parts if p).strip()
        if chart_spec:
            # Surface the chart through session state so the agent router
            # can include it on ChatResponse for the frontend to render.
            # Parallel pattern to tool_context.state["actions"].
            tool_context.state["chart"] = chart_spec

        if answer:
            result = {"status": "success", "answer": answer}
            if sql:
                result["sql"] = sql
            # Chart spec deliberately not surfaced on the result dict — it
            # flows separately via tool_context.state["chart"] for the React
            # UI to render. Telling the LLM "a chart was rendered" causes it
            # to hallucinate chart references in environments (like GE) where
            # no chart actually appears.
            return result

        return {
            "status": "error",
            "message": (
                error_text
                or "Conversational Analytics returned no answer. Try rephrasing."
            ),
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
