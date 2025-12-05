"""
Langfuse configuration for LangGraph agent observability.

Provides tracing, cost tracking, and debugging capabilities.
Supports Langfuse v3 API.
"""
import os
from typing import Optional

# Check if Langfuse is available (v3 uses langfuse.langchain)
try:
    from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    LangfuseCallbackHandler = None
    Langfuse = None

# Global Langfuse client instance
_langfuse_client: Optional["Langfuse"] = None


def get_langfuse_client() -> Optional["Langfuse"]:
    """Get or create the global Langfuse client."""
    global _langfuse_client
    
    if not LANGFUSE_AVAILABLE:
        return None
    
    if not is_langfuse_enabled():
        return None
    
    if _langfuse_client is None:
        _langfuse_client = Langfuse()
    
    return _langfuse_client


def get_langfuse_handler() -> Optional["LangfuseCallbackHandler"]:
    """
    Create a Langfuse callback handler for tracing LangGraph agent execution.
    
    In Langfuse v3, the handler reads credentials from environment variables:
    - LANGFUSE_PUBLIC_KEY
    - LANGFUSE_SECRET_KEY  
    - LANGFUSE_HOST (optional, defaults to cloud.langfuse.com)
    
    Use update_trace_context() to set session_id, user_id after handler creation.
        
    Returns:
        LangfuseCallbackHandler if configured, None otherwise
    """
    if not LANGFUSE_AVAILABLE:
        print("ℹ️  Langfuse not installed. Skipping observability.")
        return None
    
    if not is_langfuse_enabled():
        print("ℹ️  Langfuse not configured (missing LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY)")
        return None
    
    try:
        # v3 reads credentials from env vars automatically
        handler = LangfuseCallbackHandler()
        print("✅ Langfuse tracing enabled")
        return handler
    except Exception as e:
        print(f"⚠️  Failed to initialize Langfuse: {e}")
        return None


def update_trace_context(
    session_id: str,
    user_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    tags: Optional[list] = None,
) -> None:
    """
    Update the current trace with session context.
    
    Call this from within a traced function to add session/user info.
    
    Args:
        session_id: Session ID for grouping related traces
        user_id: Optional user identifier for per-user analytics
        metadata: Optional metadata to attach to traces
        tags: Optional tags for filtering traces
    """
    client = get_langfuse_client()
    if client is None:
        return
    
    try:
        client.update_current_trace(
            name="langgraph-agent",
            session_id=session_id,
            user_id=user_id,
            metadata=metadata or {},
            tags=tags or ["langgraph", "bedrock-agentcore"],
            version=os.environ.get("AGENT_VERSION", "1.0.0"),
        )
    except Exception as e:
        print(f"⚠️  Failed to update trace context: {e}")


def flush_langfuse() -> None:
    """Flush pending traces to Langfuse."""
    client = get_langfuse_client()
    if client:
        try:
            client.flush()
        except Exception as e:
            print(f"⚠️  Failed to flush Langfuse: {e}")


def is_langfuse_enabled() -> bool:
    """Check if Langfuse is available and configured."""
    if not LANGFUSE_AVAILABLE:
        return False
    
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    
    return bool(public_key and secret_key)
