"""
Langfuse configuration for LangGraph agent observability.

Provides tracing, cost tracking, and debugging capabilities.
"""
import os
from typing import Optional

# Check if Langfuse is available
try:
    from langfuse.callback import CallbackHandler as LangfuseCallbackHandler
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    LangfuseCallbackHandler = None


def get_langfuse_handler(
    session_id: str,
    user_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    tags: Optional[list] = None,
) -> Optional["LangfuseCallbackHandler"]:
    """
    Create a Langfuse callback handler for tracing LangGraph agent execution.
    
    Args:
        session_id: Session ID for grouping related traces
        user_id: Optional user identifier for per-user analytics
        metadata: Optional metadata to attach to traces
        tags: Optional tags for filtering traces
        
    Returns:
        LangfuseCallbackHandler if configured, None otherwise
    """
    if not LANGFUSE_AVAILABLE:
        print("ℹ️  Langfuse not installed. Skipping observability.")
        return None
    
    # Check for required environment variables
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    
    if not public_key or not secret_key:
        print("ℹ️  Langfuse not configured (missing LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY)")
        return None
    
    try:
        # Support both LANGFUSE_HOST and LANGFUSE_BASE_URL
        host = os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
        
        handler = LangfuseCallbackHandler(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            session_id=session_id,
            user_id=user_id,
            release=os.environ.get("AGENT_VERSION", "1.0.0"),
            trace_name="langgraph-agent",
            metadata=metadata or {},
            tags=tags or ["langgraph", "bedrock-agentcore"],
        )
        print(f"✅ Langfuse tracing enabled for session: {session_id}")
        return handler
    except Exception as e:
        print(f"⚠️  Failed to initialize Langfuse: {e}")
        return None


def is_langfuse_enabled() -> bool:
    """Check if Langfuse is available and configured."""
    if not LANGFUSE_AVAILABLE:
        return False
    
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    
    return bool(public_key and secret_key)

