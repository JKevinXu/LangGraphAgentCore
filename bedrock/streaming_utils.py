"""
Streaming utilities for Server-Sent Events (SSE) and event formatting.
"""
import json
from typing import Any, Dict, AsyncIterator
from datetime import datetime
from enum import Enum


class StreamEventType(str, Enum):
    """Event types for streaming responses."""
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    AGENT_STEP = "agent_step"
    LLM_START = "llm_start"
    LLM_TOKEN = "llm_token"
    LLM_END = "llm_end"
    TOOL_START = "tool_start"
    TOOL_PROGRESS = "tool_progress"
    TOOL_END = "tool_end"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class StreamEvent:
    """Represents a streaming event."""
    
    def __init__(
        self,
        event_type: StreamEventType,
        data: Dict[str, Any],
        metadata: Dict[str, Any] = None
    ):
        self.event_type = event_type
        self.data = data
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "type": self.event_type,
            "data": self.data,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }
    
    def to_sse(self) -> str:
        """Format event as SSE (Server-Sent Events)."""
        event_dict = self.to_dict()
        return f"event: {self.event_type}\ndata: {json.dumps(event_dict['data'])}\n\n"
    
    def to_json(self) -> str:
        """Format event as JSON line."""
        return json.dumps(self.to_dict()) + "\n"


def format_sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """Format data as SSE event."""
    event = StreamEvent(event_type, data)
    return event.to_sse()


def format_json_event(event_type: str, data: Dict[str, Any]) -> str:
    """Format data as JSON line."""
    event = StreamEvent(event_type, data)
    return event.to_json()


async def stream_with_heartbeat(
    stream: AsyncIterator[StreamEvent],
    heartbeat_interval: int = 30
) -> AsyncIterator[StreamEvent]:
    """
    Add heartbeat events to keep connection alive.
    
    Args:
        stream: Original event stream
        heartbeat_interval: Seconds between heartbeats
        
    Yields:
        StreamEvent: Events with periodic heartbeats
    """
    import asyncio
    
    last_heartbeat = datetime.now()
    
    async for event in stream:
        yield event
        
        # Send heartbeat if needed
        now = datetime.now()
        if (now - last_heartbeat).total_seconds() > heartbeat_interval:
            yield StreamEvent(
                StreamEventType.HEARTBEAT,
                {"timestamp": now.isoformat()}
            )
            last_heartbeat = now


class TokenBuffer:
    """Buffer tokens before streaming for efficiency."""
    
    def __init__(self, buffer_size: int = 5):
        self.buffer_size = buffer_size
        self.buffer = []
        self.index = 0
    
    def add(self, token: str) -> str | None:
        """
        Add token to buffer.
        
        Returns:
            str: Buffered tokens if buffer is full, None otherwise
        """
        self.buffer.append(token)
        
        if len(self.buffer) >= self.buffer_size:
            result = "".join(self.buffer)
            self.buffer.clear()
            return result
        
        return None
    
    def flush(self) -> str:
        """Flush remaining tokens in buffer."""
        if self.buffer:
            result = "".join(self.buffer)
            self.buffer.clear()
            return result
        return ""


def extract_node_output(event: Dict[str, Any]) -> Dict[str, Any]:
    """Extract useful output from LangGraph node event."""
    if not event:
        return {}
    
    # Handle different event structures
    if isinstance(event, dict):
        # Extract messages if present
        if "messages" in event:
            messages = event["messages"]
            if messages and isinstance(messages, list):
                last_msg = messages[-1]
                if hasattr(last_msg, "content"):
                    return {"content": last_msg.content, "type": last_msg.type}
        
        # Return raw event if no special structure
        return event
    
    return {"raw": str(event)}


async def stream_generator(
    async_iterator: AsyncIterator[Any],
    format_fn=None
) -> AsyncIterator[str]:
    """
    Generic async stream generator with optional formatting.
    
    Args:
        async_iterator: Source async iterator
        format_fn: Optional formatting function
        
    Yields:
        str: Formatted stream data
    """
    try:
        async for item in async_iterator:
            if format_fn:
                yield format_fn(item)
            else:
                yield str(item)
    except Exception as e:
        # Yield error event
        error_event = StreamEvent(
            StreamEventType.ERROR,
            {
                "error": str(e),
                "type": type(e).__name__
            }
        )
        yield error_event.to_sse()

