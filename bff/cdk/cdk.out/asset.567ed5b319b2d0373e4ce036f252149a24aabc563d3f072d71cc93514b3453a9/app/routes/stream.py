"""Streaming endpoint - forwards to Bedrock AgentCore with SSE."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from app.services.agent_client import get_agent_client

router = APIRouter()


class StreamRequest(BaseModel):
    """Stream request payload."""
    message: str
    session_id: Optional[str] = None
    actor_id: Optional[str] = "default"


@router.post("/chat/stream")
async def chat_stream(request: StreamRequest):
    """
    Send message to agent with streaming response (SSE).
    
    Forwards request to Bedrock AgentCore and streams response.
    """
    session_id = request.session_id or f"session-{hash(request.message) % 100000}"
    
    try:
        client = get_agent_client()
        
        return StreamingResponse(
            client.invoke_stream(
                prompt=request.message,
                session_id=session_id,
                actor_id=request.actor_id
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

