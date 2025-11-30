"""
Agent Client - Bridge between BFF and AWS Bedrock AgentCore

Uses queue-based producer-consumer pattern for streaming:
- Producer: Invokes Bedrock AgentCore and pushes events to queue
- Consumer: SSE Generator yields from queue

Reference: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/response-streaming.html
"""
import boto3
import json
import logging
import asyncio
from typing import AsyncIterator, Optional
from dataclasses import dataclass
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class StreamEvent:
    """Streaming event pushed to queue."""
    event_type: str  # agent_start, tool_start, tool_end, message, error, done
    data: dict


class StreamingCallbackHandler:
    """
    Queue-based handler for streaming events.
    Producer pushes events, Consumer yields them.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.queue: asyncio.Queue[Optional[StreamEvent]] = asyncio.Queue()
    
    async def push_event(self, event_type: str, data: dict) -> None:
        """Producer: Push event to queue."""
        await self.queue.put(StreamEvent(event_type=event_type, data=data))
    
    async def get_event(self, timeout: float = 60.0) -> Optional[StreamEvent]:
        """Consumer: Get event from queue with timeout."""
        try:
            return await asyncio.wait_for(self.queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
    
    async def end_streaming(self) -> None:
        """Signal completion with sentinel."""
        await self.queue.put(None)


class AgentClient:
    """Client for Bedrock AgentCore with queue-based streaming."""
    
    def __init__(self):
        self.client = boto3.client(
            "bedrock-agentcore",
            region_name=settings.AWS_REGION
        )
        self.runtime_arn = settings.AGENT_RUNTIME_ARN
        logger.info(f"AgentClient initialized for: {self.runtime_arn}")
    
    async def invoke(
        self,
        prompt: str,
        session_id: str,
        actor_id: str = "default"
    ) -> str:
        """Forward request to Bedrock AgentCore (blocking)."""
        payload = json.dumps({
            "prompt": prompt,
            "session_id": session_id,
            "actor_id": actor_id
        })
        
        try:
            response = self.client.invoke_agent_runtime(
                agentRuntimeArn=self.runtime_arn,
                runtimeSessionId=session_id,
                payload=payload,
                qualifier="DEFAULT"
            )
            
            streaming_body = response.get("response")
            if streaming_body and hasattr(streaming_body, "read"):
                result = streaming_body.read()
                if isinstance(result, bytes):
                    result = result.decode("utf-8")
            else:
                result = str(response)
            
            return result
            
        except Exception as e:
            logger.error(f"Error invoking agent: {e}")
            raise
    
    async def _process_bedrock_request(
        self,
        prompt: str,
        session_id: str,
        actor_id: str,
        callback: StreamingCallbackHandler
    ) -> None:
        """
        Producer: Invokes Bedrock AgentCore and pushes events to queue.
        
        This runs in a background task, iterating over the agent's
        response and pushing each event to the queue immediately.
        """
        payload = json.dumps({
            "prompt": prompt,
            "session_id": session_id,
            "actor_id": actor_id,
            "stream": True
        })
        
        try:
            # Push start event
            await callback.push_event("agent_start", {
                "session_id": session_id,
                "status": "started"
            })
            
            # Run boto3 call in thread (it's synchronous)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.invoke_agent_runtime(
                    agentRuntimeArn=self.runtime_arn,
                    runtimeSessionId=session_id,
                    payload=payload,
                    qualifier="DEFAULT"
                )
            )
            
            streaming_body = response.get("response")
            
            if streaming_body:
                # Read and parse the response
                raw_data = streaming_body.read()
                if isinstance(raw_data, bytes):
                    raw_data = raw_data.decode("utf-8")
                
                # Parse SSE events from agent runtime
                events = self._parse_agent_events(raw_data)
                
                # Push each event to queue with small delay for visual streaming
                last_content = ""
                for event_type, event_data in events:
                    logger.info(f"Pushing event: {event_type}")
                    
                    if event_type == "AGENT_START":
                        # Already pushed above
                        pass
                    elif event_type == "TOOL_CALL":
                        await callback.push_event("tool_start", {
                            "tool": event_data.get("tool", "unknown"),
                            "args": event_data.get("args", {})
                        })
                        await asyncio.sleep(0.1)  # Visual delay
                    elif event_type == "TOOL_RESULT":
                        await callback.push_event("tool_end", {
                            "tool": event_data.get("tool", "unknown"),
                            "result": event_data.get("result", "")
                        })
                        await asyncio.sleep(0.1)  # Visual delay
                    elif event_type == "LLM_RESPONSE":
                        content = event_data.get("content", "")
                        if content and content != last_content:
                            await callback.push_event("message", {
                                "content": content,
                                "partial": True
                            })
                            last_content = content
                    elif event_type == "AGENT_END":
                        output = event_data.get("output", "")
                        if output and output != last_content:
                            await callback.push_event("message", {
                                "content": output,
                                "final": True
                            })
                    elif event_type == "ERROR":
                        await callback.push_event("error", event_data)
            
        except Exception as e:
            logger.error(f"Producer error: {e}")
            await callback.push_event("error", {"error": str(e)})
        
        finally:
            # Signal completion
            await callback.end_streaming()
    
    def _parse_agent_events(self, raw_response: str) -> list:
        """Parse agent runtime's wrapped SSE format."""
        events = []
        chunks = raw_response.split('\ndata: ')
        
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            
            if chunk.startswith('data: '):
                chunk = chunk[6:]
            
            try:
                if chunk.startswith('"') and chunk.endswith('"'):
                    inner = json.loads(chunk)
                else:
                    inner = chunk
                
                event_type = None
                event_data = None
                
                for line in inner.split('\n'):
                    line = line.strip()
                    if line.startswith('event:'):
                        event_type = line[6:].strip()
                    elif line.startswith('data:'):
                        try:
                            event_data = json.loads(line[5:].strip())
                        except json.JSONDecodeError:
                            event_data = {"raw": line[5:].strip()}
                
                if event_type and event_data:
                    events.append((event_type, event_data))
                    
            except Exception as e:
                logger.warning(f"Failed to parse chunk: {e}")
                continue
        
        return events
    
    async def invoke_stream(
        self,
        prompt: str,
        session_id: str,
        actor_id: str = "default"
    ) -> AsyncIterator[str]:
        """
        Stream response using queue-based producer-consumer pattern.
        
        Architecture:
        - Producer (background task): Calls Bedrock, pushes events to queue
        - Consumer (this generator): Yields SSE from queue
        """
        # Create callback handler with queue
        callback = StreamingCallbackHandler(session_id)
        
        # Start event
        yield f"event: start\ndata: {json.dumps({'session_id': session_id})}\n\n"
        
        # Spawn producer as background task
        producer_task = asyncio.create_task(
            self._process_bedrock_request(prompt, session_id, actor_id, callback)
        )
        
        try:
            # Consumer: Yield events from queue
            while True:
                event = await callback.get_event(timeout=120.0)
                
                if event is None:  # Sentinel - streaming complete
                    break
                
                # Format as SSE
                yield f"event: {event.event_type}\ndata: {json.dumps(event.data)}\n\n"
            
            # Done event
            yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"
            
        except Exception as e:
            logger.error(f"Consumer error: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        
        finally:
            # Ensure producer task completes
            if not producer_task.done():
                producer_task.cancel()
                try:
                    await producer_task
                except asyncio.CancelledError:
                    pass


# Singleton instance
_client = None

def get_agent_client() -> AgentClient:
    """Get or create AgentClient singleton."""
    global _client
    if _client is None:
        _client = AgentClient()
    return _client
