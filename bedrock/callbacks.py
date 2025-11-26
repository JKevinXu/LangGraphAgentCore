"""
Callback handlers for streaming events.
"""
from typing import Any, Dict, List, Optional
from langchain_core.callbacks import AsyncCallbackHandler
from streaming_utils import StreamEvent, StreamEventType
import asyncio
import logging

logger = logging.getLogger(__name__)


class BaseStreamCallback(AsyncCallbackHandler):
    """Base callback handler for streaming events."""
    
    def __init__(self):
        super().__init__()
        self.events: List[StreamEvent] = []
        self._queue: Optional[asyncio.Queue] = None
    
    def set_queue(self, queue: asyncio.Queue):
        """Set the queue for event emission."""
        self._queue = queue
    
    async def emit_event(self, event: StreamEvent):
        """Emit an event to the queue."""
        self.events.append(event)
        if self._queue:
            await self._queue.put(event)
    
    async def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any
    ) -> None:
        """Called when LLM starts."""
        event = StreamEvent(
            StreamEventType.LLM_START,
            {
                "prompts": prompts[:1],  # Only first prompt to avoid spam
                "model": serialized.get("name", "unknown")
            }
        )
        await self.emit_event(event)
    
    async def on_llm_new_token(
        self,
        token: str,
        **kwargs: Any
    ) -> None:
        """Called when LLM produces a new token."""
        event = StreamEvent(
            StreamEventType.LLM_TOKEN,
            {"token": token}
        )
        await self.emit_event(event)
    
    async def on_llm_end(
        self,
        response: Any,
        **kwargs: Any
    ) -> None:
        """Called when LLM finishes."""
        event = StreamEvent(
            StreamEventType.LLM_END,
            {
                "status": "completed",
                "generations": len(response.generations) if hasattr(response, 'generations') else 0
            }
        )
        await self.emit_event(event)
    
    async def on_llm_error(
        self,
        error: Exception,
        **kwargs: Any
    ) -> None:
        """Called when LLM errors."""
        event = StreamEvent(
            StreamEventType.ERROR,
            {
                "error": str(error),
                "type": type(error).__name__,
                "source": "llm"
            }
        )
        await self.emit_event(event)
    
    async def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any
    ) -> None:
        """Called when tool starts."""
        event = StreamEvent(
            StreamEventType.TOOL_START,
            {
                "tool": serialized.get("name", "unknown"),
                "input": input_str[:200]  # Truncate long inputs
            }
        )
        await self.emit_event(event)
    
    async def on_tool_end(
        self,
        output: str,
        **kwargs: Any
    ) -> None:
        """Called when tool ends."""
        event = StreamEvent(
            StreamEventType.TOOL_END,
            {
                "output": output[:200] if isinstance(output, str) else str(output)[:200]
            }
        )
        await self.emit_event(event)
    
    async def on_tool_error(
        self,
        error: Exception,
        **kwargs: Any
    ) -> None:
        """Called when tool errors."""
        event = StreamEvent(
            StreamEventType.ERROR,
            {
                "error": str(error),
                "type": type(error).__name__,
                "source": "tool"
            }
        )
        await self.emit_event(event)
    
    async def on_agent_action(
        self,
        action: Any,
        **kwargs: Any
    ) -> None:
        """Called when agent takes action."""
        logger.debug(f"Agent action: {action}")
    
    async def on_agent_finish(
        self,
        finish: Any,
        **kwargs: Any
    ) -> None:
        """Called when agent finishes."""
        logger.debug(f"Agent finish: {finish}")


class ConsoleStreamCallback(BaseStreamCallback):
    """Callback that logs events to console."""
    
    async def emit_event(self, event: StreamEvent):
        """Emit event and log to console."""
        await super().emit_event(event)
        print(f"[{event.event_type}] {event.data}")


class MetricsCallback(BaseStreamCallback):
    """Callback that collects metrics."""
    
    def __init__(self):
        super().__init__()
        self.metrics = {
            "tokens": 0,
            "tool_calls": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
    
    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Track token count."""
        await super().on_llm_new_token(token, **kwargs)
        self.metrics["tokens"] += 1
    
    async def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any
    ) -> None:
        """Track tool calls."""
        await super().on_tool_start(serialized, input_str, **kwargs)
        self.metrics["tool_calls"] += 1
    
    async def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Track errors."""
        await super().on_llm_error(error, **kwargs)
        self.metrics["errors"] += 1
    
    async def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        """Track errors."""
        await super().on_tool_error(error, **kwargs)
        self.metrics["errors"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        return self.metrics.copy()


class QueueCallback(BaseStreamCallback):
    """Callback that puts all events into an async queue."""
    
    def __init__(self, queue: asyncio.Queue):
        super().__init__()
        self.set_queue(queue)


def create_callbacks(
    enable_console: bool = False,
    enable_metrics: bool = True,
    event_queue: Optional[asyncio.Queue] = None
) -> List[BaseStreamCallback]:
    """
    Create callback handlers.
    
    Args:
        enable_console: Enable console logging
        enable_metrics: Enable metrics collection
        event_queue: Queue for event streaming
        
    Returns:
        List of callback handlers
    """
    callbacks = []
    
    if enable_console:
        callbacks.append(ConsoleStreamCallback())
    
    if enable_metrics:
        callbacks.append(MetricsCallback())
    
    if event_queue:
        callbacks.append(QueueCallback(event_queue))
    
    return callbacks

