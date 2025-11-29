"""
LangGraphAgentCore BFF - API Router/Proxy

This is a thin API layer that routes requests to AWS Bedrock AgentCore.
No agent logic here - just request forwarding with auth and rate limiting.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.routes import health, chat, stream, websocket

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info(f"🚀 BFF starting - forwarding to: {settings.AGENT_RUNTIME_ARN}")
    yield
    logger.info("👋 BFF shutting down")


app = FastAPI(
    title="LangGraphAgentCore BFF",
    description="API Router for LangGraph Agent on Bedrock AgentCore",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router, tags=["Health"])
app.include_router(chat.router, prefix="/v1", tags=["Chat"])
app.include_router(stream.router, prefix="/v1", tags=["Streaming"])
app.include_router(websocket.router, prefix="/v1", tags=["WebSocket"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)

