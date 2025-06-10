"""Rate limiting middleware"""

import time
from typing import Dict, Optional

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from neuravox.api.models.database import ApiKey


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware based on API keys"""
    
    def __init__(self, app, default_rate_limit: int = 60):
        super().__init__(app)
        self.default_rate_limit = default_rate_limit
        self.rate_limit_storage: Dict[str, Dict[str, int]] = {}
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/api/v1/health", "/api/docs", "/api/redoc", "/api/openapi.json"]:
            return await call_next(request)
        
        # Get API key from request
        api_key = self._extract_api_key(request)
        
        if api_key:
            # Check rate limit for authenticated requests
            if not self._check_rate_limit(api_key, self.default_rate_limit):
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please try again later."
                )
        else:
            # Apply stricter rate limiting for unauthenticated requests
            client_ip = self._get_client_ip(request)
            if not self._check_rate_limit(f"ip:{client_ip}", 10):  # 10 requests per minute for unauthenticated
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please authenticate with an API key for higher limits."
                )
        
        response = await call_next(request)
        return response
    
    def _extract_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from request headers"""
        
        # Try Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]
        
        # Try X-API-Key header
        return request.headers.get("X-API-Key")
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        
        # Check for forwarded headers (when behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _check_rate_limit(self, identifier: str, limit: int) -> bool:
        """Check if request is within rate limit"""
        
        current_minute = int(time.time() // 60)
        
        if identifier not in self.rate_limit_storage:
            self.rate_limit_storage[identifier] = {}
        
        user_storage = self.rate_limit_storage[identifier]
        
        # Clean up old entries (keep only current and previous minute)
        for minute in list(user_storage.keys()):
            if minute < current_minute - 1:
                del user_storage[minute]
        
        # Get current count
        current_count = user_storage.get(current_minute, 0)
        
        if current_count >= limit:
            return False
        
        # Increment counter
        user_storage[current_minute] = current_count + 1
        
        return True


class APIKeyRateLimitMiddleware:
    """Enhanced rate limiting that respects API key limits"""
    
    def __init__(self):
        self.rate_limit_storage: Dict[str, Dict[str, int]] = {}
    
    def check_api_key_rate_limit(self, api_key_record: ApiKey) -> bool:
        """Check rate limit for authenticated API key"""
        
        return self._check_rate_limit(
            f"key:{api_key_record.id}",
            api_key_record.rate_limit_per_minute
        )
    
    def _check_rate_limit(self, identifier: str, limit: int) -> bool:
        """Check if request is within rate limit"""
        
        current_minute = int(time.time() // 60)
        
        if identifier not in self.rate_limit_storage:
            self.rate_limit_storage[identifier] = {}
        
        user_storage = self.rate_limit_storage[identifier]
        
        # Clean up old entries
        for minute in list(user_storage.keys()):
            if minute < current_minute - 1:
                del user_storage[minute]
        
        # Get current count
        current_count = user_storage.get(current_minute, 0)
        
        if current_count >= limit:
            return False
        
        # Increment counter
        user_storage[current_minute] = current_count + 1
        
        return True


# Global rate limiter instance
api_key_rate_limiter = APIKeyRateLimitMiddleware()