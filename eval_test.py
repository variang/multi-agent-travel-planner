"""Evaluation runner with canned test cases for WanderWise."""

import asyncio

from dotenv import load_dotenv

load_dotenv()

from main import run_query  # noqa: E402
from tracing_utils import flush_traces, is_tracing_enabled  # noqa: E402


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
        print(f"\n{'=' * 60}")
        print(f"Query: {case['label']}")
        print(f"Input: {case['input']}")
        print("=" * 60)
        response = await run_query(case["input"], case["state"])
        print(response)


if __name__ == "__main__":
    asyncio.run(main())
    if is_tracing_enabled():
        flush_traces()
        print("\nTraces sent to Langfuse.")
