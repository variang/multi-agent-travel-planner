"""Coordinator agent and async wrapper tools that route to sub-agents."""

from typing import Any, Optional

from google.adk.agents import Agent
from google.adk.memory import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents import (
    itinerary_agent,
    latest_events_agent,
    packing_list_agent,
    personalized_itinerary_agent,
    weather_agent,
)

APP_NAME = "wanderwise"
USER_ID = "default_user"
SESSION_ID = "default_session"

common_session_service = InMemorySessionService()
common_memory_service = InMemoryMemoryService()

MODEL = "gemini-2.5-flash"


async def _run_sub_agent(agent_instance: Agent, user_input: str, tool_context: Any) -> str:
    """Runs a sub-agent and returns its final text response."""
    sub_runner = Runner(
        agent=agent_instance,
        app_name=APP_NAME,
        session_service=common_session_service,
        memory_service=common_memory_service,
    )
    sub_content = types.Content(role="user", parts=[types.Part(text=user_input)])
    final_response = ""
    for event in sub_runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=sub_content):
        if hasattr(event, "content") and event.content and hasattr(event.content, "parts"):
            if event.is_final_response():
                parts = [p.text for p in event.content.parts if hasattr(p, "text") and p.text]
                final_response = "\n".join(parts)
    return final_response or "No response from agent."


async def call_itinerary_agent(
    destination: str, duration: str, interests: Optional[str] = None, tool_context=None
) -> str:
    """Plans a detailed travel itinerary for a given destination, duration, and interests.
    Args:
        destination: The travel destination (e.g., "Paris").
        duration: The length of the trip (e.g., "3 days").
        interests: Optional interests (e.g., "fashion and food").
    Returns:
        The generated travel itinerary in Markdown format.
    """
    print(f"--- Coordinator → itinerary_agent ({destination}, {duration}) ---")
    prompt = f"Plan a {duration} trip to {destination}"
    if interests:
        prompt += f" with interests in {interests}."
    return await _run_sub_agent(itinerary_agent, prompt, tool_context)


async def call_latest_events_agent(destination: str, timeframe: str, tool_context=None) -> str:
    """Finds current or upcoming events, festivals, or activities for a given destination and timeframe.
    Args:
        destination: The travel destination (e.g., "Paris").
        timeframe: The date or date range (e.g., "July 2025").
    Returns:
        A summary of found events in Markdown format.
    """
    print(f"--- Coordinator → latest_events_agent ({destination}, {timeframe}) ---")
    return await _run_sub_agent(
        latest_events_agent,
        f"What events are happening in {destination} in {timeframe}?",
        tool_context,
    )


async def call_weather_agent_current(city: str, tool_context=None) -> str:
    """Retrieves current weather data for a given city.
    Args:
        city: The city for which to get current weather.
    Returns:
        A report on the current weather.
    """
    print(f"--- Coordinator → weather_agent current ({city}) ---")
    return await _run_sub_agent(weather_agent, f"What's the current weather in {city}?", tool_context)


async def call_weather_agent_forecast(city: str, date_expr: str, tool_context=None) -> str:
    """Summarizes weather data for a given city and flexible date expression.
    Args:
        city: The city for which to get the forecast.
        date_expr: The date or date range (e.g., "tomorrow", "next week").
    Returns:
        A summary of the weather forecast.
    """
    print(f"--- Coordinator → weather_agent forecast ({city}, {date_expr}) ---")
    return await _run_sub_agent(
        weather_agent,
        f"What's the weather forecast for {city} on {date_expr}?",
        tool_context,
    )


async def call_personalized_itinerary_agent(
    itinerary: str, latest_events: str, tool_context=None
) -> str:
    """Personalizes a travel itinerary by integrating relevant events.
    Args:
        itinerary: The full base itinerary in Markdown format.
        latest_events: A summary of relevant events in Markdown format.
    Returns:
        The personalized itinerary in Markdown format.
    """
    print("--- Coordinator → personalized_itinerary_agent ---")
    prompt = f"Input Itinerary:\n{itinerary}\n\nInput Latest Events:\n{latest_events}"
    return await _run_sub_agent(personalized_itinerary_agent, prompt, tool_context)


async def call_packing_list_agent(
    personalized_itinerary: str, weather: str, tool_context=None
) -> str:
    """Generates a packing list based on a detailed itinerary and weather summary.
    Args:
        personalized_itinerary: The personalized itinerary in Markdown format.
        weather: The weather summary or forecast for the trip.
    Returns:
        The generated packing list in Markdown format.
    """
    print("--- Coordinator → packing_list_agent ---")
    prompt = f"Input Personalized Itinerary:\n{personalized_itinerary}\n\nInput Weather Summary:\n{weather}"
    return await _run_sub_agent(packing_list_agent, prompt, tool_context)


wanderwise_coordinator_agent = Agent(
    name="wanderwise_coordinator_agent",
    model=MODEL,
    description=(
        "An intelligent travel assistant that orchestrates specialized sub-agents "
        "(itinerary planning, event search, weather lookup, packing list generation, "
        "and personalization) to provide comprehensive travel assistance."
    ),
    instruction="""
You are the central coordinator for the WanderWise travel assistant.
Your goal is comprehensive travel assistance: personalized itinerary, events, weather, and packing list.

**Available Tools:**
- `call_itinerary_agent(destination, duration, interests)` — detailed day-by-day itinerary.
- `call_latest_events_agent(destination, timeframe)` — events and festivals.
- `call_weather_agent_current(city)` — current weather.
- `call_weather_agent_forecast(city, date_expr)` — weather forecast.
- `call_personalized_itinerary_agent(itinerary, latest_events)` — merge itinerary + events.
- `call_packing_list_agent(personalized_itinerary, weather)` — packing list.

**Full Trip Planning Flow (use for requests with destination + duration):**
1. Call `call_itinerary_agent` → store result as `itinerary_output`.
2. Call `call_latest_events_agent` → store result as `events_output`.
3. Call `call_weather_agent_forecast` → store result as `weather_output`.
4. Call `call_personalized_itinerary_agent(itinerary_output, events_output)` → `personalized_output`.
5. Call `call_packing_list_agent(personalized_output, weather_output)` → `packing_output`.
6. Return a consolidated Markdown response:

```
Here is your comprehensive travel plan for [Destination]:

### Personalized Itinerary
[personalized_output]

### Event Information
[events_output]

### Weather Forecast
[weather_output]

### Packing List
[packing_output]
```

**Single-purpose queries:**
- Only weather → call `call_weather_agent_current` or `call_weather_agent_forecast`.
- Only events → call `call_latest_events_agent`.
- Only packing list without context → ask for destination, duration, and dates first.

**Error Handling:**
- If a required field (destination, duration, timeframe) is missing, politely ask for it.
- If a tool returns an error or empty result, note it clearly in the final response.
- If the query is unrelated to travel, state your limitations and offer travel assistance.

Preserve all Markdown formatting, especially `[Item Name](URL)` hyperlinks from sub-agents.
""",
    tools=[
        call_itinerary_agent,
        call_latest_events_agent,
        call_weather_agent_current,
        call_weather_agent_forecast,
        call_personalized_itinerary_agent,
        call_packing_list_agent,
    ],
    output_key="wanderwise_plan",
)
