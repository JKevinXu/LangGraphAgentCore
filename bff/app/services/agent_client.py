"""
Agent Client - Proxy to AWS Bedrock AgentCore

This client forwards requests to the deployed agent with true streaming support.
Parses the agent runtime's wrapped SSE format and re-emits events to the frontend.
"""
import boto3
import json
import logging
import asyncio
import re
from typing import AsyncIterator
from app.config import settings

logger = logging.getLogger(__name__)


def parse_agent_runtime_events(raw_response: str) -> list:
    """
    Parse the agent runtime's wrapped SSE format.
    
    The agent runtime returns events like:
    data: "event: AGENT_START\ndata: {...}\n\n"
    data: "event: TOOL_CALL\ndata: {...}\n\n"
    ...
    
    Returns list of (event_type, event_data) tuples.
    """
    events = []
    
    # Split by "data: " prefix (each chunk is a JSON-escaped SSE event)
    chunks = raw_response.split('\ndata: ')
    
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
            
        # Remove leading "data: " if present (for first chunk)
        if chunk.startswith('data: '):
            chunk = chunk[6:]
        
        # Parse the JSON-escaped string
        try:
            # The chunk should be a JSON string like "event: ...\ndata: ...\n\n"
            if chunk.startswith('"') and chunk.endswith('"'):
                inner = json.loads(chunk)
            else:
                inner = chunk
            
            # Now parse the inner SSE event
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
                
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse chunk: {chunk[:100]}... - {e}")
            continue
    
    return events


class AgentClient:
    """Client for forwarding requests to AWS Bedrock AgentCore with streaming."""
    
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
        """
        Forward request to Bedrock AgentCore (blocking).
        """
        payload = json.dumps({
            "prompt": prompt,
            "session_id": session_id,
            "actor_id": actor_id
        })
        
        logger.info(f"Invoking agent: session={session_id}, prompt={prompt[:50]}...")
        
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
            
            logger.info(f"Agent response: {result[:100]}...")
            return result
            
        except Exception as e:
            logger.error(f"Error invoking agent: {e}")
            raise
    
    async def invoke_stream(
        self,
        prompt: str,
        session_id: str,
        actor_id: str = "default"
    ) -> AsyncIterator[str]:
        """
        Forward request to Bedrock AgentCore with streaming.
        
        Parses the agent runtime's wrapped SSE format and re-emits
        events in standard SSE format for the frontend.
        """
        payload = json.dumps({
            "prompt": prompt,
            "session_id": session_id,
            "actor_id": actor_id,
            "stream": True
        })
        
        logger.info(f"Streaming invoke: session={session_id}")
        
        # Start event
        yield f"event: start\ndata: {json.dumps({'session_id': session_id})}\n\n"
        
        try:
            # Call boto3 synchronously (it doesn't support async)
            response = await asyncio.get_event_loop().run_in_executor(
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
                # Read the full response
                raw_data = streaming_body.read()
                if isinstance(raw_data, bytes):
                    raw_data = raw_data.decode("utf-8")
                
                logger.info(f"Raw response length: {len(raw_data)}")
                
                # Parse the wrapped SSE events
                events = parse_agent_runtime_events(raw_data)
                logger.info(f"Parsed {len(events)} events")
                
                # Track last content to avoid duplicates
                last_content = ""
                
                # Re-emit events with frontend-friendly names
                for event_type, event_data in events:
                    logger.info(f"Emitting event: {event_type}")
                    
                    if event_type == "AGENT_START":
                        yield f"event: agent_start\ndata: {json.dumps(event_data)}\n\n"
                    elif event_type == "TOOL_CALL":
                        yield f"event: tool_start\ndata: {json.dumps({'tool': event_data.get('tool', 'unknown'), 'args': event_data.get('args', {})})}\n\n"
                    elif event_type == "TOOL_RESULT":
                        yield f"event: tool_end\ndata: {json.dumps({'tool': event_data.get('tool', 'unknown'), 'result': event_data.get('result', '')})}\n\n"
                    elif event_type == "LLM_RESPONSE":
                        content = event_data.get("content", "")
                        if content and content != last_content:
                            yield f"event: message\ndata: {json.dumps({'content': content, 'partial': True})}\n\n"
                            last_content = content
                    elif event_type == "AGENT_END":
                        output = event_data.get("output", "")
                        # Only emit if different from last LLM_RESPONSE
                        if output and output != last_content:
                            yield f"event: message\ndata: {json.dumps({'content': output, 'final': True})}\n\n"
                    elif event_type == "ERROR":
                        yield f"event: error\ndata: {json.dumps(event_data)}\n\n"
                    
                    # Small delay between events for visual effect
                    await asyncio.sleep(0.05)
            
            yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


# Singleton instance
_client = None

def get_agent_client() -> AgentClient:
    """Get or create AgentClient singleton."""
    global _client
    if _client is None:
        _client = AgentClient()
    return _client
