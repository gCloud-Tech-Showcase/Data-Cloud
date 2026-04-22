"""Agent chat endpoint — The Archivist powered by ADK.

Provides POST /api/agent/chat for the frontend chat panel.
Uses ADK Runner with InMemorySessionService for conversation state.
"""

import logging
import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agent.agent import root_agent

logger = logging.getLogger(__name__)

router = APIRouter()

APP_NAME = "video-search-agent"
USER_ID = "web_user"

_session_service = InMemorySessionService()
_runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=_session_service,
)


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""


class ChatResponse(BaseModel):
    text: str
    actions: list[dict]
    session_id: str


def _get_library_context() -> dict:
    """Load library stats for agent instruction interpolation."""
    try:
        from services.bigquery import get_library_stats
        stats = get_library_stats()
        categories = ", ".join(c["name"] for c in stats.get("categories", []))
        return {
            "total_videos": stats.get("total_videos", 0),
            "earliest_year": stats.get("earliest_year", "unknown"),
            "latest_year": stats.get("latest_year", "unknown"),
            "categories": categories or "various",
            "actions": [],
        }
    except Exception:
        return {
            "total_videos": "unknown",
            "earliest_year": "unknown",
            "latest_year": "unknown",
            "categories": "various",
            "actions": [],
        }


@router.post("/api/agent/chat")
async def agent_chat(request: ChatRequest) -> ChatResponse:
    session_id = request.session_id or str(uuid.uuid4())

    # Get or create session
    session = await _session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )
    if not session:
        session = await _session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session_id,
            state=_get_library_context(),
        )

    # Run the agent
    user_message = types.Content(
        role="user",
        parts=[types.Part(text=request.message)],
    )

    final_text = ""
    try:
        async for event in _runner.run_async(
            user_id=USER_ID,
            session_id=session_id,
            new_message=user_message,
            state_delta={"actions": []},
        ):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        final_text += part.text
    except Exception:
        logger.exception("Agent execution failed")
        return ChatResponse(
            text="Sorry, something went wrong processing your request. Please try again.",
            actions=[],
            session_id=session_id,
        )

    # Read actions accumulated by tools during this invocation
    updated_session = await _session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )
    actions = list(updated_session.state.get("actions", []))

    return ChatResponse(
        text=final_text or "I wasn't able to generate a response. Please try again.",
        actions=actions,
        session_id=session_id,
    )
