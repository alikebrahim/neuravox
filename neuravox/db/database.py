"""Database connection and session management"""

import os
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from neuravox.shared.config import UnifiedConfig


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


class DatabaseManager:
    """Database connection and session manager"""
    
    def __init__(self, config: UnifiedConfig):
        self.config = config
        self._engine = None
        self._session_factory = None
        
    def get_database_url(self) -> str:
        """Get database URL from config or environment"""
        # Check environment variable first
        if db_url := os.getenv("API_DATABASE_URL"):
            return db_url
        
        # Default to SQLite in workspace
        db_path = self.config.workspace / "neuravox_api.db"
        return f"sqlite+aiosqlite:///{db_path}"
    
    @property
    def engine(self):
        """Get or create database engine"""
        if self._engine is None:
            database_url = self.get_database_url()
            
            # Configure engine based on database type
            if database_url.startswith("sqlite"):
                connect_args = {"check_same_thread": False}
                self._engine = create_async_engine(
                    database_url,
                    connect_args=connect_args,
                    echo=False
                )
            else:
                # PostgreSQL or other databases
                self._engine = create_async_engine(
                    database_url,
                    pool_size=10,
                    max_overflow=20,
                    echo=False
                )
        
        return self._engine
    
    @property
    def session_factory(self):
        """Get or create session factory"""
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
        return self._session_factory
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session"""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def create_tables(self):
        """Create all database tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def drop_tables(self):
        """Drop all database tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    async def close(self):
        """Close database connections"""
        if self._engine:
            await self._engine.dispose()


# Global database manager instance
_db_manager: DatabaseManager = None


def get_database_manager(config: UnifiedConfig = None) -> DatabaseManager:
    """Get or create global database manager"""
    global _db_manager
    if _db_manager is None:
        if config is None:
            config = UnifiedConfig()
        _db_manager = DatabaseManager(config)
    return _db_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session"""
    db_manager = get_database_manager()
    async for session in db_manager.get_session():
        yield session