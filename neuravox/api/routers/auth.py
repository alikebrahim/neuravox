"""Authentication and API key management endpoints"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from neuravox.db.database import get_db_session
from neuravox.api.services.auth_service import AuthService
from neuravox.api.models.requests import CreateApiKeyRequest
from neuravox.api.models.responses import ApiKeyResponse, CreateApiKeyResponse
from neuravox.api.models.database import ApiKey
from neuravox.api.middleware.auth import get_current_api_key, require_api_key
from neuravox.api.utils.exceptions import NotFoundError, AuthenticationError


router = APIRouter()


def get_auth_service() -> AuthService:
    """Dependency for auth service"""
    return AuthService()


@router.post("/auth/keys", response_model=CreateApiKeyResponse, status_code=201)
async def create_api_key(
    request: CreateApiKeyRequest,
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new API key"""
    
    try:
        api_key, db_api_key = await auth_service.create_api_key(
            name=request.name,
            user_id=request.user_id,
            rate_limit_per_minute=request.rate_limit_per_minute,
            db=db
        )
        
        return CreateApiKeyResponse(
            key=api_key,
            id=db_api_key.id,
            name=db_api_key.name,
            user_id=db_api_key.user_id,
            created_at=db_api_key.created_at,
            last_used_at=db_api_key.last_used_at,
            is_active=db_api_key.is_active,
            rate_limit_per_minute=db_api_key.rate_limit_per_minute
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create API key: {str(e)}")


@router.get("/auth/keys", response_model=List[ApiKeyResponse])
async def list_api_keys(
    current_api_key: Optional[ApiKey] = Depends(get_current_api_key),
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db_session)
):
    """List API keys (filtered by current user if authenticated)"""
    
    try:
        # If authenticated, only show keys for current user
        user_id = current_api_key.user_id if current_api_key else None
        
        api_keys = await auth_service.list_api_keys(user_id=user_id, db=db)
        
        return [
            ApiKeyResponse(
                id=key.id,
                name=key.name,
                user_id=key.user_id,
                created_at=key.created_at,
                last_used_at=key.last_used_at,
                is_active=key.is_active,
                rate_limit_per_minute=key.rate_limit_per_minute
            )
            for key in api_keys
        ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list API keys: {str(e)}")


@router.get("/auth/keys/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    key_id: str,
    current_api_key: ApiKey = Depends(require_api_key),
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db_session)
):
    """Get API key details"""
    
    try:
        api_key = await auth_service.get_api_key_by_id(key_id, db)
        
        if not api_key:
            raise NotFoundError("API key", key_id)
        
        # Only allow users to see their own keys (unless admin - TODO: implement admin role)
        if api_key.user_id != current_api_key.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return ApiKeyResponse(
            id=api_key.id,
            name=api_key.name,
            user_id=api_key.user_id,
            created_at=api_key.created_at,
            last_used_at=api_key.last_used_at,
            is_active=api_key.is_active,
            rate_limit_per_minute=api_key.rate_limit_per_minute
        )
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get API key: {str(e)}")


@router.delete("/auth/keys/{key_id}", status_code=204)
async def deactivate_api_key(
    key_id: str,
    current_api_key: ApiKey = Depends(require_api_key),
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db_session)
):
    """Deactivate an API key"""
    
    try:
        # Get the key to check ownership
        api_key = await auth_service.get_api_key_by_id(key_id, db)
        
        if not api_key:
            raise NotFoundError("API key", key_id)
        
        # Only allow users to deactivate their own keys
        if api_key.user_id != current_api_key.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Prevent deactivating the key being used for this request
        if api_key.id == current_api_key.id:
            raise HTTPException(status_code=400, detail="Cannot deactivate the API key being used for this request")
        
        success = await auth_service.deactivate_api_key(key_id, db)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to deactivate API key")
        
        return
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to deactivate API key: {str(e)}")


@router.get("/auth/me", response_model=ApiKeyResponse)
async def get_current_user(
    current_api_key: ApiKey = Depends(require_api_key)
):
    """Get current user information from API key"""
    
    return ApiKeyResponse(
        id=current_api_key.id,
        name=current_api_key.name,
        user_id=current_api_key.user_id,
        created_at=current_api_key.created_at,
        last_used_at=current_api_key.last_used_at,
        is_active=current_api_key.is_active,
        rate_limit_per_minute=current_api_key.rate_limit_per_minute
    )