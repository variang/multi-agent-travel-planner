# Langfuse Integration Guide - WanderWise

## Configuration

Add the following to your `.env` file:

```bash
LANGFUSE_PUBLIC_KEY="pk-lf-..."
LANGFUSE_SECRET_KEY="sk-lf-..."

# LANGFUSE_HOST  — read by the Python SDK (required)
# LANGFUSE_BASE_URL — read by the Langfuse CLI (keep both in sync)
LANGFUSE_HOST="http://localhost:3000"
LANGFUSE_BASE_URL="http://localhost:3000"
```

> **Important:** The Langfuse v2 Python SDK reads `LANGFUSE_HOST`, **not** `LANGFUSE_BASE_URL`.
> If only `LANGFUSE_BASE_URL` is set, the SDK silently falls back to `https://cloud.langfuse.com`
> and your traces will not appear in your local dashboard.

## Overview

This document explains the Langfuse tracing integration added to the WanderWise multi-agent travel planner. The integration follows Langfuse best practices for observability and enables detailed monitoring of all agent orchestration and API calls.

## What Was Added

### 1. **Dependencies** (`requirements.txt`)
- Added `langfuse>=2.51.0,<3` for LLM observability

### 2. **Tracing Utilities** (`tracing_utils.py`)
Core module providing:
- Langfuse client initialization
- Trace and span creation helpers
- Decorators for automatic function tracing
- Utility functions for different span types

### 3. **Coordinator Integration** (`coordinator.py`)
- Added context variable (`_trace_id_context`) for passing trace IDs through async calls
- Updated all agent calling functions to create child spans
- Each agent call is traced with:
  - Descriptive span name: `call-{agent_type}-agent`
  - Input prompt
  - Agent response (first 500 chars for readability)
  - Relevant tags (`itinerary`, `events`, `weather`, etc.)

### 4. **Main Entry Point** (`main.py`)
- Creates root trace for each query with user context
- Sets trace ID in context for child spans to inherit
- Captures query input and final response
- Calls `flush_traces()` on exit to ensure all traces are sent

### 5. **Example Script** (`eval_test_with_tracing.py`)
- Demonstrates complete traced execution
- Shows how to integrate tracing with async workflows
- Includes helpful output for exploring traces in Langfuse UI

## Trace Structure

Every travel planning request creates a hierarchical trace:

```
wanderwise-travel-request (root trace)
├── call-itinerary-agent
├── call-events-agent
├── call-weather-agent
├── call-personalizer-agent
└── call-packing-agent
```

Each span captures:
- **input**: The prompt or query sent to the agent
- **model**: The LLM model used (`gemini-2.5-flash`)
- **output**: The agent's response (truncated for large responses)
- **tags**: For filtering and analysis

## Best Practices Implemented

### 1. **Initialization Order**
- Langfuse is initialized AFTER environment variables are loaded
- This prevents credential issues and initialization errors
- Location: `main.py` (after `load_dotenv()`)

### 2. **Descriptive Naming**
- Trace names are meaningful: `wanderwise-travel-request`, `call-itinerary-agent`
- Makes traces easily discoverable and filterable in Langfuse UI
- Enables quick identification of which agent/step failed

### 3. **Context Management**
- Uses Python's `contextvars` to pass trace IDs through async calls
- Avoids needing to thread trace IDs through function parameters
- Ensures child spans are properly associated with parent traces

### 4. **User & Session Tracking**
- Every trace includes `user_id` and `session_id`
- Enables filtering by user in Langfuse
- Groups related queries in Sessions view

### 5. **Hierarchical Spans**
- Sub-agent calls are nested spans, not root traces
- Shows which step is slow or failing
- Enables performance analysis per agent

### 6. **Safe Data Handling**
- Large outputs are truncated (500 chars for agent responses)
- Prevents leaking sensitive data or overwhelming Langfuse
- Preserves key information for debugging

### 7. **Guaranteed Flushing**
- `flush_traces()` is called in `finally` block
- Ensures traces are sent even if an error occurs
- Critical for scripts that exit quickly

## Usage

### Interactive CLI
```bash
python main.py
```
- Type travel planning queries
- Each query is traced and sent to Langfuse
- Type 'exit' to quit (traces are flushed automatically)

### Programmatic Example
```bash
python eval_test_with_tracing.py
```
- Runs a complete trace of a Barcelona trip planning
- Demonstrates correct async/await patterns
- Flushes traces and confirms they were sent

## Viewing Traces in Langfuse

### 1. **Connect to Langfuse**
Visit: `http://localhost:3000` (or your configured `LANGFUSE_HOST`)

### 2. **Find Your Traces**
- Navigate to "Traces" view
- Filter by:
  - **user_id**: `default_user`
  - **session_id**: `default_session`
  - **tags**: `coordinator`, `sub-agent`, specific agent types

### 3. **Explore Trace Details**
- Click a trace to expand its hierarchy
- View input/output for each agent
- See timing information
- Identify bottlenecks

### 4. **Build Dashboards**
- Create custom dashboards using tags
- Track performance per agent type
- Monitor error rates
- Analyze user behavior patterns

## Metrics Available in Langfuse

After running queries, you can analyze:

| Metric | Location | Use Case |
|--------|----------|----------|
| Latency | Trace details | Find slow agents |
| Token usage | Span output | Estimate costs |
| Error rates | Trace filters | Identify reliability issues |
| User patterns | Session view | Understand usage |
| Agent performance | Filter by agent tag | Compare agent quality |

## Extending the Integration

### Add Tracing to New Functions
Use the provided decorators:

```python
from tracing_utils import observe_async, observe_sync

@observe_async("my-async-function", tags=["important"])
async def my_function(x: int) -> int:
    return x * 2

@observe_sync("my-sync-function", tags=["utility"])
def my_other_function(y: str) -> str:
    return y.upper()
```

### Trace Tool Calls
For external API calls, use the helper:

```python
from tracing_utils import trace_tool_call

trace_id = _trace_id_context.get()
if trace_id:
    trace_tool_call(
        trace_id=trace_id,
        tool_name="google_search",
        tool_input="Paris restaurants",
        tool_output="Top 10 restaurants in Paris...",
    )
```

### Add Custom Spans
For complex logic:

```python
from tracing_utils import get_langfuse_client

langfuse = get_langfuse_client()
trace_id = _trace_id_context.get()

span = langfuse.span(
    name="my-custom-step",
    trace_id=trace_id,
    input={"key": "value"},
    output={"result": "output"},
    tags=["custom"],
)
span.end()
```

## Troubleshooting

### Traces Not Appearing
1. Check `.env` file has valid `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`
2. Set **`LANGFUSE_HOST`** to your server URL (e.g., `http://localhost:3000`) — this is the env var the **Python SDK** reads. `LANGFUSE_BASE_URL` is only used by the CLI and docs, **not** the Python client.
3. Ensure `flush_traces()` is called before exit
4. Check Langfuse server is running/accessible

### Missing Child Spans
1. Verify `_trace_id_context` is set before agent calls
2. Check that trace ID is not None
3. Ensure spans have `trace_id` parameter set

### Large Output Sizes
- Outputs are truncated to 500 characters
- Full outputs available in logs if needed
- Consider implementing custom truncation for specific agents

## Performance Impact

- **Minimal overhead**: Langfuse is async-compatible
- **Batched sends**: Traces are collected and sent in batches
- **Non-blocking**: `flush_traces()` should not significantly impact exit time
- **Scalable**: Supports any number of traces

## Security Considerations

1. **API Keys**: Store in `.env` file, never commit to version control
2. **Data Privacy**: Truncate sensitive data in inputs/outputs
3. **PII Handling**: Consider masking user data in agent responses
4. **Access Control**: Use Langfuse project settings for team access

## Next Steps

1. **Run the example**: `python eval_test_with_tracing.py`
2. **Explore traces**: Visit Langfuse dashboard and browse traces
3. **Set up dashboards**: Create custom views for your use case
4. **Add scoring**: Implement quality feedback on traces
5. **Implement experiments**: Compare agent configurations using Langfuse

## References

- [Langfuse Documentation](https://langfuse.com/docs)
- [Langfuse Python SDK](https://github.com/langfuse/langfuse-python)
- [Tracing Best Practices](https://langfuse.com/docs/observability/overview)
- [Session Tracking](https://langfuse.com/docs/tracing-features/sessions)
- [Scoring & Feedback](https://langfuse.com/docs/scores/overview)

## Support

For issues with:
- **Langfuse SDK**: Check [GitHub issues](https://github.com/langfuse/langfuse-python/issues)
- **Integration**: Review `tracing_utils.py` for correct usage patterns
- **Configuration**: Verify `.env` credentials and server connectivity
