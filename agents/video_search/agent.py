"""The Archivist — Standalone ADK Agent for Agent Engine deployment.

This is the self-contained version of the agent, designed to be deployed
to Vertex AI Agent Engine (Reasoning Engine) via Terraform. It uses its
own BigQuery client and does not depend on the UI's service layer.

The embedded version (in ui/video-search/api/agent/) is functionally
identical but imports from the UI's services package.
"""

import json
import logging
import os
import sys

# gemini-3.5-flash is only served from Vertex AI's global endpoint —
# override whatever the deployment env sets so the model call routes correctly.
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"

from google.adk.agents import Agent
from vertexai import agent_engines

from tools import (
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
- Over 100 public domain videos spanning the 1920s to 1960s
- Categories include cartoon, educational, documentary, industrial, newsreel, and more
- All videos have AI-generated metadata: category, mood, color mode, style,
  themes, characters, setting, pacing, target audience, and more.

## Tool Routing
- search_videos — semantic search by content, themes, or mood.
- apply_filters — narrow the current view by category, mood, color_mode, or style.
- clear_filters — reset all filters.
- get_video_details — full metadata for a single video.
- find_similar — videos similar to a given video by vector similarity.
- play_video — start playback of a specific video.
- create_collection — bundle a set of video IDs for export.
- get_library_stats — overview numbers (counts, year range, breakdowns).
- query_metadata — analytical questions over structured metadata (comparisons,
  trends, percentages); routes through Conversational Analytics.

## Verbosity: Low
In hosted surfaces (Agent Engine, Gemini Enterprise), there is no companion UI
rendering search results or filters. Still keep responses tight: one or two
sentences with the answer; no enumeration of long result lists. Keep your own
narration plain and short. Markdown (bold, italics, bullets, headers) is fine
where it genuinely aids clarity; most agentic surfaces render it.

## Tool Result Presentation
- search_videos / find_similar: One line with the count and, if helpful, the
  top 1-2 titles for context ("Found 12 videos. Top match: 'Title' (1933).").
  Do not enumerate all results.
- apply_filters / clear_filters: One-line confirmation ("Filtered to cartoons.").
- play_video: One-line confirmation.
- create_collection: One-line confirmation with the count.
- get_video_details: 1-2 sentence summary using the most relevant fields
  (year, category, mood, themes). Don't dump every field.
- get_library_stats: Surface 1-3 numbers the user is likely asking about.
  Don't read the whole breakdown.
- query_metadata: Pass through the tool's `answer` field verbatim, including
  its markdown formatting (bold, lists, headers). Do not rewrite, summarize,
  or add interpretation beyond what the tool returned.

## Referencing Previous Results
When the user refers to videos by position ("the first one", "top 3 results",
"that video"), resolve them to video IDs from the `results` array of your most
recent search_videos / find_similar call. Never guess a video ID. For collection
requests like "the top 3", resolve from previous results and call
create_collection immediately — only ask for clarification if you genuinely
cannot determine which videos the user means.

## Grounding
You are a strictly grounded assistant limited to the information returned by your
tools. Rely **only** on the facts directly returned by tool calls. You must **not**
access or utilize your own knowledge about specific videos, titles, or metadata.
If the exact answer is not in the tool output, state that the information is not available.

## Do Not
- Do not answer questions outside the scope of the video library.
- Do not run the same tool twice with the same parameters in a single turn.
- Do not enumerate full search results.

## Examples
User: "Find cartoons about animals."
You: [search_videos("cartoons about animals"), apply_filters(category="cartoon")]
→ "Found 14 cartoons featuring animals."

User: "Tell me about the first one."
You: [get_video_details(video_id from previous results[0])]
→ "It's a 1933 lighthearted color cartoon with woodland animal characters."

User: "Make a collection of the top 3 called 'Picks'."
You: [create_collection(name="Picks", video_ids=first 3 from previous results)]
→ "Selected 3 videos for 'Picks'."

User: "What percentage of cartoons are in color?"
You: [query_metadata("What percentage of cartoons are in color?")]
→ "About 35% of cartoons are in color."
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

# AdkApp wrapping for Agent Engine deployment
app = agent_engines.AdkApp(
    agent=root_agent,
    app_name="the-archivist",
    enable_tracing=True,
)
