"""Application configuration settings."""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # AWS
    AWS_REGION: str = "us-west-2"
    AGENT_RUNTIME_ARN: str = ""
    
    # Authentication
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    API_KEYS: str = ""  # Comma-separated string
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    
    # Timeouts
    REQUEST_TIMEOUT: int = 300  # 5 minutes
    STREAM_TIMEOUT: int = 600   # 10 minutes
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def api_keys_list(self) -> List[str]:
        """Parse API keys from comma-separated string."""
        if self.API_KEYS:
            return [k.strip() for k in self.API_KEYS.split(",") if k.strip()]
        return []


settings = Settings()

