"""
Agent Client - Proxy to AWS Bedrock AgentCore

This client forwards requests to the deployed agent and parses
SSE-formatted streaming responses for re-emission to frontends.
"""
import boto3
import json
import logging
import re
from typing import AsyncIterator
from app.config import settings

logger = logging.getLogger(__name__)


def parse_sse_events(raw_response: str) -> list:
    """
    Parse SSE-formatted response into a list of events.
    
    Args:
        raw_response: Raw SSE string from agent runtime
        
    Returns:
        List of dicts with 'event' and 'data' keys
    """
    events = []
    
    # Handle JSON-encoded string (double-encoded)
    content = raw_response.strip()
    try:
        decoded = json.loads(content)
        if isinstance(decoded, str):
            content = decoded
    except json.JSONDecodeError:
        pass
    
    # Split by double newlines to get individual events
    event_strings = re.split(r'\n\n+', content)
    
    for event_str in event_strings:
        if not event_str.strip():
            continue
        
        event_type = None
        event_data = None
        
        for line in event_str.strip().split('\n'):
            line = line.strip()
            if line.startswith('event:'):
                event_type = line[6:].strip()
            elif line.startswith('data:'):
                data_str = line[5:].strip()
                try:
                    event_data = json.loads(data_str)
                except json.JSONDecodeError:
                    event_data = {"raw": data_str}
        
        if event_type and event_data:
            events.append({"event": event_type, "data": event_data})
    
    return events


def extract_final_output(events: list) -> str:
    """
    Extract the final output from a list of SSE events.
    
    Args:
        events: List of parsed SSE events
        
    Returns:
        Final output string
    """
    final_output = ""
    
    for event in events:
        event_type = event.get("event", "")
        data = event.get("data", {})
        
        if event_type == "AGENT_END":
            final_output = data.get("output", "")
        elif event_type == "LLM_RESPONSE" and not final_output:
            final_output = data.get("content", "")
    
    return final_output


class AgentClient:
    """Client for forwarding requests to AWS Bedrock AgentCore."""
    
    def __init__(self):
        self.client = boto3.client(
            "bedrock-agentcore",
            region_name=settings.AWS_REGION
        )
        self.runtime_arn = settings.AGENT_RUNTIME_ARN
        logger.info(f"AgentClient initialized for: {self.runtime_arn}")
    
    def _read_response_body(self, response: dict) -> str:
        """Extract raw response string from Bedrock AgentCore response."""
        streaming_body = response.get("response")
        if streaming_body and hasattr(streaming_body, "read"):
            result = streaming_body.read()
            if isinstance(result, bytes):
                return result.decode("utf-8")
            return result
        
        body = response.get("body")
        if body and hasattr(body, "read"):
            result = body.read()
            if isinstance(result, bytes):
                return result.decode("utf-8")
            return result
        
        return str(response)
    
    async def invoke(
        self,
        prompt: str,
        session_id: str,
        actor_id: str = "default"
    ) -> str:
        """
        Forward request to Bedrock AgentCore (blocking, non-streaming).
        
        Args:
            prompt: User message
            session_id: Session identifier
            actor_id: Actor identifier
            
        Returns:
            Agent response string
        """
        payload = json.dumps({
            "prompt": prompt,
            "session_id": session_id,
            "actor_id": actor_id,
            "stream": False
        })
        
        logger.info(f"Invoking agent: session={session_id}, prompt={prompt[:50]}...")
        
        try:
            response = self.client.invoke_agent_runtime(
                agentRuntimeArn=self.runtime_arn,
                runtimeSessionId=session_id,
                payload=payload,
                qualifier="DEFAULT"
            )
            
            result = self._read_response_body(response)
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
        
        Parses SSE events from agent runtime and re-emits them
        to the frontend with proper event types.
        
        Args:
            prompt: User message
            session_id: Session identifier
            actor_id: Actor identifier
            
        Yields:
            SSE-formatted event strings for frontend consumption
        """
        payload = json.dumps({
            "prompt": prompt,
            "session_id": session_id,
            "actor_id": actor_id,
            "stream": True
        })
        
        logger.info(f"Streaming invoke: session={session_id}")
        
        # Emit start event immediately
        yield f"event: start\ndata: {json.dumps({'session_id': session_id})}\n\n"
        
        try:
            response = self.client.invoke_agent_runtime(
                agentRuntimeArn=self.runtime_arn,
                runtimeSessionId=session_id,
                payload=payload,
                qualifier="DEFAULT"
            )
            
            # Read the complete SSE-formatted response from agent runtime
            raw_result = self._read_response_body(response)
            logger.debug(f"Raw streaming response (first 500 chars): {raw_result[:500]}...")
            
            # Parse SSE events from agent runtime
            events = parse_sse_events(raw_result)
            logger.info(f"Parsed {len(events)} events from agent runtime")
            
            # Re-emit events to frontend
            # Track last content to avoid duplicates
            last_content = None
            
            for event in events:
                event_type = event.get("event", "")
                data = event.get("data", {})
                
                # Map agent runtime events to frontend events
                if event_type == "AGENT_START":
                    yield f"event: agent_start\ndata: {json.dumps(data)}\n\n"
                    
                elif event_type == "TOOL_CALL":
                    yield f"event: tool_start\ndata: {json.dumps(data)}\n\n"
                    
                elif event_type == "TOOL_RESULT":
                    yield f"event: tool_end\ndata: {json.dumps(data)}\n\n"
                    
                elif event_type == "LLM_RESPONSE":
                    # This is the main response content
                    content = data.get("content", "")
                    if content:
                        last_content = content
                        yield f"event: message\ndata: {json.dumps({'content': content})}\n\n"
                    
                elif event_type == "AGENT_END":
                    # Final output - only emit if different from last content
                    output = data.get("output", "")
                    if output and output != last_content:
                        yield f"event: message\ndata: {json.dumps({'content': output})}\n\n"
                    
                elif event_type == "ERROR":
                    error_msg = data.get("error", "Unknown error")
                    yield f"event: error\ndata: {json.dumps({'error': error_msg})}\n\n"
            
            # If no events were parsed, treat raw response as plain text
            if not events:
                logger.warning("No SSE events parsed, returning raw response")
                # Try to extract content from raw response
                content = raw_result.strip()
                # Handle JSON-encoded strings
                try:
                    decoded = json.loads(content)
                    if isinstance(decoded, str):
                        content = decoded
                except json.JSONDecodeError:
                    pass
                yield f"event: message\ndata: {json.dumps({'content': content})}\n\n"
            
            # Done event
            yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


# Singleton instance
_client = None

def get_agent_client() -> AgentClient:
    """Get or create AgentClient singleton."""
    global _client
    if _client is None:
        _client = AgentClient()
    return _client
