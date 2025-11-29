"""Chat endpoint - forwards to Bedrock AgentCore."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.agent_client import get_agent_client

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request payload."""
    message: str
    session_id: Optional[str] = None
    actor_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    """Chat response payload."""
    message: str
    session_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send message to agent (blocking).
    
    Forwards request to Bedrock AgentCore and returns response.
    """
    session_id = request.session_id or f"session-{hash(request.message) % 100000}"
    
    try:
        client = get_agent_client()
        response = await client.invoke(
            prompt=request.message,
            session_id=session_id,
            actor_id=request.actor_id
        )
        return ChatResponse(message=response, session_id=session_id)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

