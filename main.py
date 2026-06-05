"""Entry point — runs example queries against the WanderWise coordinator agent."""

import asyncio
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.genai import types

load_dotenv()

# Validate required env vars before importing agents (which configure the LLM backend)
_required = ["OPEN_WEATHER_API_KEY"]
for _var in _required:
    if not os.environ.get(_var):
        raise EnvironmentError(
            f"Missing required environment variable: {_var}. "
            "Please copy .env.example to .env and fill in your credentials."
        )

from coordinator import (  # noqa: E402  (import after env validation)
    APP_NAME,
    SESSION_ID,
    USER_ID,
    common_memory_service,
    common_session_service,
    wanderwise_coordinator_agent,
)


async def run_query(
    input_text: str,
    initial_state: Optional[Dict[str, Any]] = None,
) -> str:
    """Runs a single user query through the coordinator agent."""
    try:
        await common_session_service.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
        )
        if initial_state:
            session = await common_session_service.get_session(
                app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
            )
            session.state.update(initial_state)
    except Exception:
        await common_session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
            state=initial_state or {},
        )

    runner = Runner(
        agent=wanderwise_coordinator_agent,
        app_name=APP_NAME,
        session_service=common_session_service,
        memory_service=common_memory_service,
    )

    content = types.Content(role="user", parts=[types.Part(text=input_text)])
    final_response = ""
    for event in runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content):
        if hasattr(event, "content") and event.content and hasattr(event.content, "parts"):
            text_parts = [p.text for p in event.content.parts if hasattr(p, "text") and p.text]
            if text_parts:
                final_response = "\n".join(text_parts)

    return final_response or "No response from agent."


async def main() -> None:
    test_cases = [
        {
            "label": "Full trip planning (Milan)",
            "input": "I will be in Milan for 3 days this weekend. I love fashion and food. What should I pack? What events are happening? What's the weather?",
            "state": {"user_preference_temperature_unit": "metric"},
        },
        {
            "label": "Current weather only (Tokyo)",
            "input": "What's the current weather in Tokyo?",
            "state": None,
        },
        {
            "label": "Events + packing tips (Munich)",
            "input": "Munich, last week of July, beer and music. Any events? Packing must-haves?",
            "state": None,
        },
    ]

    for case in test_cases:
        print(f"\n{'='*60}")
        print(f"Query: {case['label']}")
        print(f"Input: {case['input']}")
        print("=" * 60)
        response = await run_query(case["input"], case["state"])
        print(response)


if __name__ == "__main__":
    asyncio.run(main())
