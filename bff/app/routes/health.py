"""Health check endpoints."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    """Health check for load balancer."""
    return {"status": "healthy"}


@router.get("/ready")
async def ready():
    """Readiness check."""
    return {"status": "ready"}

