"""Authentication middleware for API"""

from typing import Optional

from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from neuravox.db.database import get_db_session
from neuravox.api.services.auth_service import AuthService
from neuravox.api.models.database import ApiKey
from neuravox.api.utils.exceptions import AuthenticationError


security = HTTPBearer(auto_error=False)


class AuthenticationMiddleware:
    """Middleware for API key authentication"""
    
    def __init__(self):
        self.auth_service = AuthService()
    
    async def authenticate_api_key(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: AsyncSession = Depends(get_db_session)
    ) -> Optional[ApiKey]:
        """Authenticate API key from Authorization header or X-API-Key header"""
        
        api_key = None
        
        # Try Authorization header (Bearer token)
        if credentials and credentials.scheme.lower() == "bearer":
            api_key = credentials.credentials
        
        # Try X-API-Key header
        if not api_key:
            api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            return None
        
        # Validate API key
        api_key_record = await self.auth_service.validate_api_key(api_key, db)
        
        if not api_key_record:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired API key"
            )
        
        return api_key_record


# Global middleware instance
auth_middleware = AuthenticationMiddleware()


async def get_current_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Optional[ApiKey]:
    """Dependency to get current API key (optional authentication)"""
    return await auth_middleware.authenticate_api_key(request, credentials, db)


async def require_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> ApiKey:
    """Dependency to require API key authentication"""
    api_key = await auth_middleware.authenticate_api_key(request, credentials, db)
    
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide via Authorization header (Bearer token) or X-API-Key header"
        )
    
    return api_key


async def get_current_user_id(
    api_key: ApiKey = Depends(get_current_api_key)
) -> Optional[str]:
    """Get current user ID from API key"""
    return api_key.user_id if api_key else None


async def require_user_id(
    api_key: ApiKey = Depends(require_api_key)
) -> str:
    """Require authentication and return user ID"""
    return api_key.user_id