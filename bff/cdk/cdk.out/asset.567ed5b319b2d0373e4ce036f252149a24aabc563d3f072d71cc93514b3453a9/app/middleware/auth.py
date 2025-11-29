"""Authentication middleware - API key validation."""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings


class AuthMiddleware(BaseHTTPMiddleware):
    """Simple API key authentication."""
    
    # Paths that don't require authentication
    PUBLIC_PATHS = {"/health", "/ready", "/docs", "/openapi.json", "/redoc"}
    
    async def dispatch(self, request: Request, call_next):
        # Skip auth for public paths
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)
        
        # Check API key header
        api_key = request.headers.get("X-API-Key")
        if api_key and api_key in settings.api_keys_list:
            return await call_next(request)
        
        # No valid auth
        if settings.api_keys_list:  # Only enforce if keys are configured
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
        
        return await call_next(request)

