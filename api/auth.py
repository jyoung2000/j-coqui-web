import os
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

# Security scheme
security = HTTPBearer(auto_error=False)

# Load configuration
ENABLE_API_AUTH = os.getenv("ENABLE_API_AUTH", "false").lower() == "true"
API_KEY = os.getenv("API_KEY", "")

def get_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[str]:
    """Validate API key if authentication is enabled"""
    
    # If auth is disabled, allow all requests
    if not ENABLE_API_AUTH:
        return None
    
    # If auth is enabled, check credentials
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate API key
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return credentials.credentials

class RateLimiter:
    """Simple rate limiter"""
    
    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self.requests = {}
    
    async def check_rate_limit(self, client_ip: str) -> bool:
        """Check if client has exceeded rate limit"""
        # Implementation would track requests per IP
        # This is a placeholder
        return True

# Initialize rate limiter
rate_limiter = RateLimiter(
    requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
)
