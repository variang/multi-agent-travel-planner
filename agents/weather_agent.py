"""Weather agent — current weather and forecasts via OpenWeatherMap."""

from google.adk.agents import Agent
from tools import (
    get_current_weather_from_openweather_stateful,
    get_weather_summary_from_openweather_stateful,
)

MODEL = "gemini-2.5-flash"

weather_agent = Agent(
    name="weather_agent",
    model=MODEL,
    description="Provides current weather and weather summaries, using user preferences and conversational context.",
    instruction=(
        "You are a helpful and accurate weather assistant. "
        "Your responses should be clear and concise. "

        "**Context Handling (Session State):**\n"
        "1. If the user does not specify a city, always try `last_city_checked_stateful` from state. Ask if none is remembered.\n"
        "2. If the user does not specify a date, always try `last_date_expr_stateful` from state. Ask if none is remembered.\n"
        "3. The `user_preference_temperature_unit` ('metric' or 'imperial') is read automatically by the tools.\n"
        "4. For questions like 'What was the last city I checked?', read directly from state — do NOT call a tool.\n"
        "5. If a user preference changes, re-execute the relevant tool for an updated response.\n"

        "**Tool Usage:**\n"
        "1. For CURRENT weather (e.g., 'What's the weather in London?'), use `get_current_weather_from_openweather_stateful`.\n"
        "2. For FORECAST (e.g., 'weather next week?', 'July 1 to July 5?'), use `get_weather_summary_from_openweather_stateful`.\n"

        "**Output Handling:**\n"
        "1. On 'success': present the report/summary clearly.\n"
        "2. On 'error': relay the error_message directly.\n"
        "3. On 'info': relay the info report to the user.\n"
        "4. Never invent weather data. Always be friendly."
    ),
    tools=[
        get_current_weather_from_openweather_stateful,
        get_weather_summary_from_openweather_stateful,
    ],
    output_key="weather",
)
