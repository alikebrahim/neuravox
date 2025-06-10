"""Main FastAPI application for Neuravox API"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from neuravox.shared.config import UnifiedConfig
from neuravox.db.database import get_database_manager
from neuravox.api.routers import health, files, jobs, processing, auth, workspace
from neuravox.api.routers import config as config_router
from neuravox.api.middleware.rate_limit import RateLimitMiddleware
from neuravox.api.utils.exceptions import NeuravoxAPIException


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("Starting Neuravox API...")
    
    # Initialize database
    db_manager = get_database_manager()
    await db_manager.create_tables()
    print("Database initialized")
    
    # Ensure workspace directories exist
    config = UnifiedConfig()
    config.ensure_workspace_dirs()
    print(f"Workspace ready at: {config.workspace}")
    
    yield
    
    # Shutdown
    print("Shutting down Neuravox API...")
    await db_manager.close()


def create_app(config_path: Optional[Path] = None) -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title="Neuravox API",
        description="REST API for Neuravox audio processing and transcription platform",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )
    
    # Load configuration
    config = UnifiedConfig(config_path) if config_path else UnifiedConfig()
    app.state.config = config
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Add rate limiting middleware
    app.add_middleware(RateLimitMiddleware, default_rate_limit=60)
    
    # Exception handlers
    @app.exception_handler(NeuravoxAPIException)
    async def neuravox_exception_handler(request: Request, exc: NeuravoxAPIException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_type,
                "message": exc.message,
                "details": exc.details
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
                "details": {"exception": str(exc)} if app.debug else None
            }
        )
    
    # Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(auth.router, prefix="/api/v1", tags=["authentication"])
    app.include_router(files.router, prefix="/api/v1", tags=["files"])
    app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
    app.include_router(processing.router, prefix="/api/v1", tags=["processing"])
    app.include_router(config_router.router, prefix="/api/v1", tags=["configuration"])
    app.include_router(workspace.router, prefix="/api/v1", tags=["workspace"])
    
    return app


def get_cors_origins() -> list[str]:
    """Get CORS origins from environment"""
    origins_env = os.getenv("API_CORS_ORIGINS", "http://localhost:3000")
    return [origin.strip() for origin in origins_env.split(",")]


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    workers: int = 1,
    reload: bool = False,
    config_path: Optional[Path] = None
):
    """Run the API server"""
    app = create_app(config_path)
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        workers=workers if not reload else 1,  # reload only works with 1 worker
        reload=reload,
        access_log=True,
        log_level="info"
    )


if __name__ == "__main__":
    # For development
    run_server(reload=True)