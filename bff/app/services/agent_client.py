"""
Agent Client - Proxy to AWS Bedrock AgentCore

This client simply forwards requests to the deployed agent.
No agent logic here - just HTTP calls to Bedrock AgentCore.
"""
import boto3
import json
import logging
from typing import AsyncIterator
from app.config import settings

logger = logging.getLogger(__name__)


class AgentClient:
    """Client for forwarding requests to AWS Bedrock AgentCore."""
    
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
            "actor_id": actor_id
        })
        
        logger.debug(f"Invoking agent: session={session_id}")
        
        response = self.client.invoke_agent_runtime(
            agentRuntimeArn=self.runtime_arn,
            runtimeSessionId=session_id,
            payload=payload,
            qualifier="DEFAULT"
        )
        
        result = response["body"].read().decode("utf-8")
        logger.debug(f"Agent response received: {len(result)} chars")
        
        return result
    
    async def invoke_stream(
        self,
        prompt: str,
        session_id: str,
        actor_id: str = "default"
    ) -> AsyncIterator[str]:
        """
        Forward request to Bedrock AgentCore with streaming.
        
        Args:
            prompt: User message
            session_id: Session identifier
            actor_id: Actor identifier
            
        Yields:
            SSE-formatted event strings
        """
        payload = json.dumps({
            "prompt": prompt,
            "session_id": session_id,
            "actor_id": actor_id,
            "stream": True
        })
        
        logger.debug(f"Streaming invoke: session={session_id}")
        
        # Start event
        yield f"event: start\ndata: {json.dumps({'session_id': session_id})}\n\n"
        
        try:
            response = self.client.invoke_agent_runtime(
                agentRuntimeArn=self.runtime_arn,
                runtimeSessionId=session_id,
                payload=payload,
                qualifier="DEFAULT"
            )
            
            result = response["body"].read().decode("utf-8")
            
            # Message event
            yield f"event: message\ndata: {json.dumps({'content': result})}\n\n"
            
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

