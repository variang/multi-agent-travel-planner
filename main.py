"""Entry point for interactive WanderWise CLI usage."""

import asyncio
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.genai import types

load_dotenv()

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
    set_trace_id,
    common_memory_service,
    common_session_service,
    wanderwise_coordinator_agent,
)
from tracing_utils import flush_traces, get_langfuse_client, is_tracing_enabled  # noqa: E402


async def run_query(
    input_text: str,
    initial_state: Optional[Dict[str, Any]] = None,
) -> str:
    """Runs a single user query through the coordinator agent."""

    trace = None
    if is_tracing_enabled():
        langfuse = get_langfuse_client()
        trace = langfuse.trace(
            name="wanderwise-travel-request",
            user_id=USER_ID,
            session_id=SESSION_ID,
            input={"query": input_text},
            tags=["cli", "interactive"],
        )
        set_trace_id(trace.id)
    
    try:
        session = await common_session_service.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
        )
        if session is None:
            await common_session_service.create_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=SESSION_ID,
                state=initial_state or {},
            )
        elif initial_state:
            session.state.update(initial_state)

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

        if trace is not None:
            trace.update(output=final_response)
        return final_response or "No response from agent."
    
    finally:
        set_trace_id(None)


async def main() -> None:
    """Runs an interactive prompt loop for travel planning queries."""
    print("WanderWise Interactive CLI")
    print("Type your travel request and press Enter.")
    print("Type 'exit' or 'quit' to stop.")

    try:
        while True:
            user_input = input("\nTravel request> ").strip()
            if not user_input:
                print("Please enter a request, or type 'exit' to quit.")
                continue
            if user_input.lower() in {"exit", "quit"}:
                print("Goodbye.")
                break

            print("\n" + "=" * 60)
            response = await run_query(user_input)
            print(response)
    finally:
        # Flush all traces to Langfuse before exit
        flush_traces()
        print("\nTraces sent to Langfuse.")


if __name__ == "__main__":
    asyncio.run(main())
