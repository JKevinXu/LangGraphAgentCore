"""
Agent Client - Bridge between BFF and AWS Bedrock AgentCore

Uses aioboto3 for TRUE async streaming without buffering.
Queue-based producer-consumer pattern for SSE delivery.
"""
import aioboto3
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
    event_type: str
    data: dict


class StreamingCallbackHandler:
    """Queue-based handler for streaming events."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.queue: asyncio.Queue[Optional[StreamEvent]] = asyncio.Queue()
    
    async def push_event(self, event_type: str, data: dict) -> None:
        await self.queue.put(StreamEvent(event_type=event_type, data=data))
    
    async def get_event(self, timeout: float = 120.0) -> Optional[StreamEvent]:
        try:
            return await asyncio.wait_for(self.queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
    
    async def end_streaming(self) -> None:
        await self.queue.put(None)


class AgentClient:
    """Client for Bedrock AgentCore with TRUE async streaming via aioboto3."""
    
    def __init__(self):
        self.session = aioboto3.Session()
        self.runtime_arn = settings.AGENT_RUNTIME_ARN
        self.region = settings.AWS_REGION
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
        
        async with self.session.client("bedrock-agentcore", region_name=self.region) as client:
            response = await client.invoke_agent_runtime(
                agentRuntimeArn=self.runtime_arn,
                runtimeSessionId=session_id,
                payload=payload,
                qualifier="DEFAULT"
            )
            
            streaming_body = response.get("response")
            if streaming_body:
                result = await streaming_body.read()
                if isinstance(result, bytes):
                    result = result.decode("utf-8")
            return result
            return str(response)
    
    async def _process_bedrock_stream(
        self,
        prompt: str,
        session_id: str,
        actor_id: str,
        callback: StreamingCallbackHandler
    ) -> None:
        """
        Producer: TRUE async streaming from Bedrock AgentCore.
        
        Uses aioboto3 for async iteration over the response stream.
        Each line is pushed to the queue as soon as it arrives.
        """
        payload = json.dumps({
            "prompt": prompt,
            "session_id": session_id,
            "actor_id": actor_id,
            "stream": True
        })
        
        try:
            await callback.push_event("agent_start", {
                "session_id": session_id,
                "status": "started"
            })
            
            async with self.session.client("bedrock-agentcore", region_name=self.region) as client:
                response = await client.invoke_agent_runtime(
                    agentRuntimeArn=self.runtime_arn,
                    runtimeSessionId=session_id,
                    payload=payload,
                    qualifier="DEFAULT"
                )
                
                streaming_body = response.get("response")
                print(f"🔍 Response keys: {response.keys()}", flush=True)
                print(f"🔍 Streaming body type: {type(streaming_body)}", flush=True)
                logger.info(f"Response keys: {response.keys()}")
                logger.info(f"Streaming body type: {type(streaming_body)}")
                
                if streaming_body:
                    buffer = ""
                    last_content = ""
                    
                    # Check if it supports async iteration
                    print(f"🔍 Has iter_chunks: {hasattr(streaming_body, 'iter_chunks')}", flush=True)
                    print(f"🔍 Has __aiter__: {hasattr(streaming_body, '__aiter__')}", flush=True)
                    print(f"🔍 Has read: {hasattr(streaming_body, 'read')}", flush=True)
                    
                    if hasattr(streaming_body, 'iter_chunks'):
                        print("✅ Using iter_chunks for streaming", flush=True)
                        logger.info("Using iter_chunks for streaming")
                        chunk_iter = streaming_body.iter_chunks()
                    elif hasattr(streaming_body, '__aiter__'):
                        print("✅ Using async iteration", flush=True)
                        logger.info("Using async iteration")
                        chunk_iter = streaming_body
                    else:
                        # Fall back to reading the whole response
                        print("⚠️ No streaming support, reading full response", flush=True)
                        logger.info("No streaming support, reading full response")
                        full_data = await streaming_body.read()
                        if isinstance(full_data, bytes):
                            full_data = full_data.decode("utf-8")
                        print(f"📦 Full response data: {full_data[:500]}...", flush=True)
                        logger.info(f"Full response data: {full_data[:500]}...")
                        
                        # Try to parse and forward the response
                        try:
                            import json
                            parsed = json.loads(full_data)
                            if isinstance(parsed, str):
                                await callback.push_event("message", {
                                    "content": parsed,
                                    "final": True
                                })
                            elif isinstance(parsed, dict) and "output" in parsed:
                                await callback.push_event("message", {
                                    "content": parsed["output"],
                                    "final": True
                                })
                            else:
                                await callback.push_event("message", {
                                    "content": str(parsed),
                                    "final": True
                                })
                        except:
                            await callback.push_event("message", {
                                "content": full_data,
                                "final": True
                            })
                        return
                    
                    # TRUE ASYNC STREAMING: iterate over chunks as they arrive
                    async for chunk in chunk_iter:
                        if isinstance(chunk, tuple):
                            chunk = chunk[0]  # aioboto3 returns (chunk, metadata)
                        if isinstance(chunk, bytes):
                            chunk = chunk.decode("utf-8")
                        
                        logger.info(f"Received chunk: {len(chunk)} bytes")
                        logger.info(f"Chunk content: {chunk[:200]}...")
                        buffer += chunk
                        
                        # Process complete SSE events
                        while "\n\n" in buffer:
                            event_str, buffer = buffer.split("\n\n", 1)
                            await self._process_event(event_str, callback, last_content)
                    
                    # Process remaining buffer
                    if buffer.strip():
                        logger.info(f"Final buffer content: {buffer[:200]}...")
                        
                        # Check if it looks like SSE format
                        if buffer.startswith("event:") or buffer.startswith("data:"):
                            await self._process_event(buffer, callback, last_content)
                        else:
                            # It's plain text response from AgentCore - emit as final message
                            logger.info(f"Plain text response detected, emitting as message")
                            # Try to parse as JSON (AgentCore might return quoted string)
                            try:
                                parsed = json.loads(buffer)
                                content = parsed if isinstance(parsed, str) else str(parsed)
                            except:
                                content = buffer.strip()
                            
                            await callback.push_event("message", {
                                "content": content,
                                "final": True
                            })
        
        except Exception as e:
            logger.error(f"Producer error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            await callback.push_event("error", {"error": str(e)})
        
        finally:
            await callback.end_streaming()
    
    async def _process_event(
        self, 
        event_str: str, 
        callback: StreamingCallbackHandler,
        last_content: str
    ) -> str:
        """Parse and push a single SSE event."""
        if not event_str.strip():
            return last_content
        
        # Parse wrapped format: data: "event: ...\ndata: ...\n\n"
        event_type = None
        event_data = None
        
        if event_str.startswith('data: "'):
            try:
                inner = json.loads(event_str[6:])
                for line in inner.split('\n'):
                    line = line.strip()
                    if line.startswith('event:'):
                        event_type = line[6:].strip()
                    elif line.startswith('data:'):
                        try:
                            event_data = json.loads(line[5:].strip())
                        except:
                            event_data = {"raw": line[5:].strip()}
            except:
                pass
        else:
            for line in event_str.strip().split('\n'):
                line = line.strip()
                if line.startswith('event:'):
                    event_type = line[6:].strip()
                elif line.startswith('data:'):
                    try:
                        event_data = json.loads(line[5:].strip())
                    except:
                        event_data = {"raw": line[5:].strip()}
        
        if event_type and event_data:
            logger.info(f"Pushing event: {event_type}")
            
            if event_type == "TOOL_CALL":
                await callback.push_event("tool_start", {
                    "tool": event_data.get("tool", "unknown"),
                    "args": event_data.get("args", {})
                })
            elif event_type == "TOOL_RESULT":
                await callback.push_event("tool_end", {
                    "tool": event_data.get("tool", "unknown"),
                    "result": event_data.get("result", "")
                })
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
        
        return last_content
    
    async def invoke_stream(
        self,
        prompt: str,
        session_id: str,
        actor_id: str = "default"
    ) -> AsyncIterator[str]:
        """
        Stream response using TRUE async streaming.
        
        Producer spawns background task that streams from Bedrock.
        Consumer yields SSE events from queue immediately.
        """
        callback = StreamingCallbackHandler(session_id)
        
        yield f"event: start\ndata: {json.dumps({'session_id': session_id})}\n\n"
            
        # Spawn producer
        producer_task = asyncio.create_task(
            self._process_bedrock_stream(prompt, session_id, actor_id, callback)
        )
        
        try:
            while True:
                event = await callback.get_event(timeout=120.0)
                
                if event is None:
                    break
                
                yield f"event: {event.event_type}\ndata: {json.dumps(event.data)}\n\n"
            
            yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"
            
        except Exception as e:
            logger.error(f"Consumer error: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        finally:
            if not producer_task.done():
                producer_task.cancel()
                try:
                    await producer_task
                except asyncio.CancelledError:
                    pass


_client = None

def get_agent_client() -> AgentClient:
    global _client
    if _client is None:
        _client = AgentClient()
    return _client
