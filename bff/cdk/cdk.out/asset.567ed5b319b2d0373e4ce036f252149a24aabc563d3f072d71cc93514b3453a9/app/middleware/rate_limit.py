"""Rate limiting middleware - simple in-memory limiter."""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
import time
from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting."""
    
    PUBLIC_PATHS = {"/health", "/ready"}
    
    def __init__(self, app):
        super().__init__(app)
        self.requests = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limit for health checks
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)
        
        # Get client identifier
        client_id = (
            request.headers.get("X-API-Key") or 
            request.client.host if request.client else "unknown"
        )
        
        now = time.time()
        window = settings.RATE_LIMIT_WINDOW
        limit = settings.RATE_LIMIT_REQUESTS
        
        # Clean old requests
        self.requests[client_id] = [
            t for t in self.requests[client_id]
            if now - t < window
        ]
        
        # Check limit
        if len(self.requests[client_id]) >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {limit} requests per {window}s"
            )
        
        # Record request
        self.requests[client_id].append(now)
        
        return await call_next(request)

