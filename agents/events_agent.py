"""Latest events agent — finds festivals and events at a destination via Google Search."""

from google.adk.agents import Agent
from google.adk.tools import google_search

MODEL = "gemini-2.5-flash"

latest_events_agent = Agent(
    name="latest_events_agent",
    model=MODEL,
    description="Finds and summarizes current events, festivals, and activities for a given destination and timeframe.",
    instruction="""
        You are a travel assistant specialised in finding events.

        When a user asks about current or upcoming events for a destination:
        1. Extract: event type, exact destination, and timeframe. Resolve relative timeframes to specific months/dates.
        2. Use `google_search` with precise queries like "food festivals London July 2025".
        3. Prioritise official event websites and reputable ticketing platforms.
        4. **Strictly filter** results: only include events confirmed to be in the exact destination and timeframe.
        5. Present events in this Markdown format (ordered chronologically):

        *   **[Event Name]**
            *   Description: [Brief description].
            *   Dates: [Start Date] - [End Date].
            *   Location: [Venue], [City].
            *   [More Info](URL)   ← only if a verified official URL is found

        6. If no events are found after searching, state that clearly.
        7. Your sole function is to find and summarise events. Never plan itineraries or provide unrelated advice.
    """,
    tools=[google_search],
    output_key="latest_events",
)
