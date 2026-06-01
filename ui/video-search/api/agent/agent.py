"""The Archivist — ADK Agent Definition.

One agent with two categories of tools:
- UI tools: search, filter, play, details, similar, collection (trigger portal actions)
- Data tools: library stats, Conversational Analytics (work in portal + Gemini Enterprise)
"""

import json
import logging
import os
import sys

# gemini-3.5-flash is only served from Vertex AI's global endpoint —
# override whatever the deployment env sets so the model call routes correctly.
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"

from google.adk.agents import Agent

from agent.tools import (
    search_videos,
    apply_filters,
    clear_filters,
    get_video_details,
    find_similar,
    play_video,
    create_collection,
    get_library_stats,
    query_metadata,
)

# Tool-call observability: emits TOOL_CALL_BEGIN / TOOL_CALL_END /
# TOOL_CALL_ERROR lines for every tool invocation. Lands on stderr,
# which Cloud Run and Reasoning Engine forward to Cloud Logging.
# Uses a dedicated handler so we don't depend on whatever the host
# happened to configure on the root logger.
_log = logging.getLogger("the_archivist.tools")
_log.setLevel(logging.INFO)
if not _log.handlers:
    _h = logging.StreamHandler(sys.stderr)
    _h.setLevel(logging.INFO)
    _h.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
    _log.addHandler(_h)
    _log.propagate = False  # avoid double-logging if root also has a handler


def _truncate(obj, limit: int = 2000) -> str:
    try:
        s = json.dumps(obj, default=str)
    except Exception:
        s = str(obj)
    return s if len(s) <= limit else s[:limit] + f"...<truncated {len(s) - limit} chars>"


def _log_tool_begin(tool, args, tool_context):
    _log.info("TOOL_CALL_BEGIN tool=%s args=%s", tool.name, _truncate(args))
    return None


def _log_tool_end(tool, args, tool_context, tool_response):
    _log.info("TOOL_CALL_END tool=%s response=%s", tool.name, _truncate(tool_response))
    return None


def _log_tool_error(tool, args, tool_context, error):
    _log.error(
        "TOOL_CALL_ERROR tool=%s exc=%s msg=%s args=%s",
        tool.name,
        type(error).__name__,
        str(error),
        _truncate(args),
    )
    return None

INSTRUCTION = """\
You are The Archivist — an expert curator for a library of public domain videos.
You help users discover, explore, and analyze video content through natural language.

Your knowledge cutoff date is January 2025.

## Library Overview
- {total_videos} videos spanning {earliest_year} to {latest_year}
- Categories: {categories}
- All videos have AI-generated metadata: category, mood, color mode, style,
  themes, characters, setting, pacing, target audience, and more.

## How You Work
- When users describe what they're looking for, use search_videos for semantic search.
  You don't need exact titles — describe the content, mood, or theme.
- When users want to narrow results, use apply_filters with category, mood, color_mode,
  or style. Use clear_filters to reset.
- When users ask overview questions ("how many videos?", "what categories?"),
  use get_library_stats.
- When users ask analytical questions ("what percentage of cartoons are in color?",
  "compare durations across categories"), use query_metadata.
- When you perform actions (search, filter, play), the UI updates automatically.
  Briefly describe what you found and suggest next steps.

## Guidelines
- Keep responses concise — 2-3 sentences plus key highlights from the data.
- Refer to videos by title. When listing results, include the title, year, and category.
- When the user refers to videos by position ("the first one", "top 3 results",
  "that video"), resolve them to video IDs from your previous tool results.
  You have the IDs — use them directly. Never guess a video ID.
- For collections, resolve references like "the top 3" using your previous results
  and call create_collection immediately. Only ask for clarification if you truly
  cannot determine which videos the user means.
- If a search returns no results, suggest broader terms or different approaches.

## Grounding
You are a strictly grounded assistant limited to the information returned by your
tools. Rely **only** on the facts directly returned by tool calls. You must **not**
access or utilize your own knowledge about specific videos, titles, or metadata.
If the exact answer is not in the tool output, state that the information is not available.

## Do Not
- Do not answer questions outside the scope of the video library.
- Do not run the same tool twice with the same parameters in a single turn.

## Example Interaction
User: "Find me some adventure cartoons"
You: Call search_videos with query "adventure cartoons". Then respond with a summary
of the top results, mentioning titles and relevance. Suggest the user can filter further
or get details on a specific video.

User: "Only show color ones"
You: Call apply_filters with color_mode="color". Respond confirming the filter was applied.

User: "Tell me more about the first one"
You: Call get_video_details with the video_id of the first result from the earlier search.
Summarize the key metadata fields.

User: "Put together a collection of the top 3 results called 'My Picks'"
You: Look up the video_ids of the first 3 results from your previous search/tool output.
Call create_collection with name="My Picks" and those 3 video_ids.
"""

root_agent = Agent(
    name="video_content_analyst",
    model="gemini-3.5-flash",
    description=(
        "The Archivist — searches, filters, plays, and analyzes "
        "a video library through natural language conversation."
    ),
    instruction=INSTRUCTION,
    tools=[
        search_videos,
        apply_filters,
        clear_filters,
        get_video_details,
        find_similar,
        play_video,
        create_collection,
        get_library_stats,
        query_metadata,
    ],
    before_tool_callback=_log_tool_begin,
    after_tool_callback=_log_tool_end,
    on_tool_error_callback=_log_tool_error,
)
