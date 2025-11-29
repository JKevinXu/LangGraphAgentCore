"""WebSocket endpoint - real-time chat via Bedrock AgentCore."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.agent_client import get_agent_client
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat.
    
    Forwards messages to Bedrock AgentCore and streams responses.
    """
    await websocket.accept()
    session_id = None
    
    try:
        client = get_agent_client()
        
        while True:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)
            
            session_id = message.get("session_id", session_id or "ws-session")
            prompt = message.get("message", "")
            actor_id = message.get("actor_id", "default")
            
            # Forward to agent and stream response
            async for event in client.invoke_stream(
                prompt=prompt,
                session_id=session_id,
                actor_id=actor_id
            ):
                await websocket.send_text(event)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011, reason=str(e))

