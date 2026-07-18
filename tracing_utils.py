"""Langfuse tracing utilities for WanderWise multi-agent system.

Langfuse is an *optional* dependency. Tracing is enabled only when:
  1. The `langfuse` package is installed, AND
  2. LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are set in the environment.

When either condition is not met the module silently provides no-op stubs so
the rest of the application works unchanged without any tracing.
"""

import functools
import logging
import os
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional Langfuse initialisation
# ---------------------------------------------------------------------------

_LANGFUSE_ENABLED = False
langfuse_client = None

_has_credentials = (
    os.environ.get("LANGFUSE_PUBLIC_KEY")
    and os.environ.get("LANGFUSE_SECRET_KEY")
)

if _has_credentials:
    try:
        from langfuse import Langfuse  # noqa: PLC0415
        _client = Langfuse()
        if not hasattr(_client, "trace") or not hasattr(_client, "span"):
            logger.warning(
                "Langfuse SDK version is incompatible (requires v2 API). "
                "Install langfuse>=2.51.0,<3. Tracing disabled."
            )
        else:
            langfuse_client = _client
            _LANGFUSE_ENABLED = True
            logger.info("Langfuse tracing enabled.")
    except ImportError:
        logger.info(
            "langfuse package not installed. Tracing disabled. "
            "Install with: pip install 'langfuse>=2.51.0,<3'"
        )
else:
    logger.info(
        "LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set. Tracing disabled."
    )


def is_tracing_enabled() -> bool:
    """Return True when Langfuse is available and configured."""
    return _LANGFUSE_ENABLED


def get_langfuse_client():
    """Return the Langfuse client, or None when tracing is disabled."""
    return langfuse_client


def flush_traces() -> None:
    """Flush all pending traces to Langfuse. No-op when tracing is disabled."""
    client = get_langfuse_client()
    if client is not None:
        client.flush()


def trace_coordinator_flow(
    destination: str,
    duration: str,
    user_id: str = "default_user",
    session_id: str = "default_session",
) -> dict[str, str]:
    """Create a root trace for the entire coordinate flow. No-op when tracing is disabled."""
    client = get_langfuse_client()
    if client is None:
        return {"trace_id": None, "trace": None}
    trace = client.trace(
        name="coordinator-travel-plan",
        user_id=user_id,
        session_id=session_id,
        input={
            "destination": destination,
            "duration": duration,
        },
        tags=["coordinator", "multi-agent"],
    )
    return {"trace_id": trace.id, "trace": trace}


def start_agent_generation(
    trace_id: str,
    agent_type: str,
    input_text: str,
    model: str,
):
    """Start a generation observation BEFORE the agent runs.

    Returns the generation object (or None when tracing is disabled).
    Pass the returned object to end_agent_generation() after the agent finishes.
    This two-phase approach captures real wall-clock latency.
    """
    client = get_langfuse_client()
    if client is None:
        return None
    gen = client.generation(
        name=f"call-{agent_type}-agent",
        trace_id=trace_id,
        input=input_text,
        model=model,
        tags=[agent_type, "sub-agent"],
    )
    gen._input_text = input_text
    return gen


def end_agent_generation(generation, output: str) -> None:
    """End a generation observation AFTER the agent finishes, recording the output."""
    if generation is None:
        return
    input_text = getattr(generation, "_input_text", "")
    generation.end(
        output=output,
        usage={
            "input": len(input_text) // 4,
            "output": len(output) // 4,
            "unit": "TOKENS",
        },
    )


def trace_agent_call(
    trace_id: str,
    agent_name: str,
    agent_type: str,
    input_text: str,
    output: str,
    model: str,
) -> None:
    """Record a sub-agent call as a generation (always zero-latency).

    Prefer start_agent_generation / end_agent_generation to capture real latency.
    """
    client = get_langfuse_client()
    if client is None:
        return
    gen = client.generation(
        name=f"call-{agent_type}-agent",
        trace_id=trace_id,
        input=input_text,
        output=output,
        model=model,
        tags=[agent_type, "sub-agent"],
    )
    gen.end()


def trace_tool_call(
    trace_id: str,
    tool_name: str,
    tool_input: str,
    tool_output: str,
) -> None:
    """Record a tool invocation (e.g., Google Search, OpenWeatherMap API).
    
    Args:
        trace_id: Parent trace ID
        tool_name: Name of the tool
        tool_input: Input to the tool
        tool_output: Tool's output (summary only for large responses)
    """
    client = get_langfuse_client()
    if client is None:
        return
    span = client.span(
        name=f"tool-{tool_name}",
        trace_id=trace_id,
        input=tool_input,
        output=tool_output,
        tags=["tool"],
    )
    span.end()


def trace_orchestration_step(
    trace_id: str,
    step_name: str,
    input_data: Any,
    output_data: Any,
) -> None:
    """Record orchestration logic step.
    
    Args:
        trace_id: Parent trace ID
        step_name: Name of the orchestration step
        input_data: Input data for this step
        output_data: Output from this step
    """
    client = get_langfuse_client()
    if client is None:
        return
    span = client.span(
        name=f"orchestration-{step_name}",
        trace_id=trace_id,
        input=input_data,
        output=output_data,
        tags=["orchestration"],
    )
    span.end()


def observe_async(
    name: str,
    tags: Optional[list[str]] = None,
) -> Callable:
    """Decorator for tracing async functions with Langfuse.
    
    Usage:
        @observe_async("my-function", tags=["test"])
        async def my_func(x: int) -> int:
            return x * 2
    
    Args:
        name: Name of the trace
        tags: Optional tags for filtering
        
    Returns:
        Decorator function
    """
    tags = tags or []
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            client = get_langfuse_client()
            if client is None:
                return await func(*args, **kwargs)
            trace = client.trace(
                name=name,
                input={"args": str(args), "kwargs": str(kwargs)},
                tags=tags,
            )
            try:
                result = await func(*args, **kwargs)
                trace.update(output=result)
                return result
            except Exception as e:
                trace.update(output={"error": str(e)})
                raise
        
        return wrapper
    
    return decorator


def observe_sync(
    name: str,
    tags: Optional[list[str]] = None,
) -> Callable:
    """Decorator for tracing sync functions with Langfuse.
    
    Usage:
        @observe_sync("my-function", tags=["test"])
        def my_func(x: int) -> int:
            return x * 2
    
    Args:
        name: Name of the trace
        tags: Optional tags for filtering
        
    Returns:
        Decorator function
    """
    tags = tags or []
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            client = get_langfuse_client()
            if client is None:
                return func(*args, **kwargs)
            trace = client.trace(
                name=name,
                input={"args": str(args), "kwargs": str(kwargs)},
                tags=tags,
            )
            try:
                result = func(*args, **kwargs)
                trace.update(output=result)
                return result
            except Exception as e:
                trace.update(output={"error": str(e)})
                raise
        
        return wrapper
    
    return decorator
