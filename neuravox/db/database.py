"""Database connection and session management"""

import os
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from neuravox.shared.config import UnifiedConfig
from neuravox.shared.logging_config import get_db_logger


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


class DatabaseManager:
    """Database connection and session manager"""
    
    def __init__(self, config: UnifiedConfig):
        self.config = config
        self.logger = get_db_logger()
        self._engine = None
        self._session_factory = None
        
        self.logger.info("Database manager initialized")
        
    def get_database_url(self) -> str:
        """Get database URL from config or environment"""
        # Check environment variable first
        if db_url := os.getenv("API_DATABASE_URL"):
            self.logger.info("Using database URL from environment variable")
            return db_url
        
        # Default to SQLite in workspace
        db_path = self.config.workspace / "neuravox_api.db"
        database_url = f"sqlite+aiosqlite:///{db_path}"
        self.logger.info(f"Using SQLite database at {str(db_path)}")
        return database_url
    
    @property
    def engine(self):
        """Get or create database engine"""
        if self._engine is None:
            database_url = self.get_database_url()
            self.logger.info("Creating database engine")
            
            # Configure engine based on database type
            if database_url.startswith("sqlite"):
                connect_args = {"check_same_thread": False}
                self._engine = create_async_engine(
                    database_url,
                    connect_args=connect_args,
                    echo=False
                )
                self.logger.info("SQLite engine created")
            else:
                # PostgreSQL or other databases
                self._engine = create_async_engine(
                    database_url,
                    pool_size=10,
                    max_overflow=20,
                    echo=False
                )
                self.logger.info("PostgreSQL/other database engine created")
        
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
        self.logger.info("Creating database tables")
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            self.logger.info("Database tables created successfully")
        except Exception as e:
            self.logger.error(f"Failed to create database tables: {str(e)}", exc_info=True)
            raise
    
    async def drop_tables(self):
        """Drop all database tables"""
        self.logger.info("Dropping database tables")
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            self.logger.info("Database tables dropped successfully")
        except Exception as e:
            self.logger.error(f"Failed to drop database tables", error=str(e), exc_info=True)
            raise
    
    async def close(self):
        """Close database connections"""
        if self._engine:
            self.logger.info("Closing database connections")
            await self._engine.dispose()
            self.logger.info("Database connections closed")


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