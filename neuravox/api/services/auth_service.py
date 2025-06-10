"""Authentication and authorization service"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from neuravox.api.models.database import ApiKey
from neuravox.api.utils.exceptions import AuthenticationError, ValidationError


class AuthService:
    """Service for managing API authentication"""
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a new API key"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash an API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    async def create_api_key(
        self,
        name: str,
        user_id: str,
        rate_limit_per_minute: int = 60,
        db: AsyncSession = None
    ) -> tuple[str, ApiKey]:
        """Create a new API key"""
        
        # Generate API key
        api_key = self.generate_api_key()
        key_hash = self.hash_api_key(api_key)
        
        # Create database record
        db_api_key = ApiKey(
            key_hash=key_hash,
            name=name,
            user_id=user_id,
            rate_limit_per_minute=rate_limit_per_minute
        )
        
        db.add(db_api_key)
        await db.commit()
        await db.refresh(db_api_key)
        
        return api_key, db_api_key
    
    async def validate_api_key(
        self,
        api_key: str,
        db: AsyncSession
    ) -> Optional[ApiKey]:
        """Validate an API key and return the associated record"""
        
        if not api_key:
            return None
        
        key_hash = self.hash_api_key(api_key)
        
        query = select(ApiKey).where(
            ApiKey.key_hash == key_hash,
            ApiKey.is_active == True
        )
        
        result = await db.execute(query)
        api_key_record = result.scalar_one_or_none()
        
        if api_key_record:
            # Update last used timestamp
            await self.update_last_used(api_key_record.id, db)
        
        return api_key_record
    
    async def update_last_used(
        self,
        api_key_id: str,
        db: AsyncSession
    ):
        """Update the last used timestamp for an API key"""
        
        query = (
            update(ApiKey)
            .where(ApiKey.id == api_key_id)
            .values(last_used_at=datetime.utcnow())
        )
        
        await db.execute(query)
        await db.commit()
    
    async def deactivate_api_key(
        self,
        api_key_id: str,
        db: AsyncSession
    ) -> bool:
        """Deactivate an API key"""
        
        query = (
            update(ApiKey)
            .where(ApiKey.id == api_key_id)
            .values(is_active=False)
        )
        
        result = await db.execute(query)
        await db.commit()
        
        return result.rowcount > 0
    
    async def list_api_keys(
        self,
        user_id: Optional[str] = None,
        db: AsyncSession = None
    ) -> list[ApiKey]:
        """List API keys, optionally filtered by user"""
        
        query = select(ApiKey).where(ApiKey.is_active == True)
        
        if user_id:
            query = query.where(ApiKey.user_id == user_id)
        
        query = query.order_by(ApiKey.created_at.desc())
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_api_key_by_id(
        self,
        api_key_id: str,
        db: AsyncSession
    ) -> Optional[ApiKey]:
        """Get API key by ID"""
        
        query = select(ApiKey).where(ApiKey.id == api_key_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()