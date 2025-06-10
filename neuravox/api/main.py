"""Main FastAPI application for Neuravox API"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from neuravox.shared.config import UnifiedConfig
from neuravox.shared.logging_config import configure_logging, get_logger
from neuravox.db.database import get_database_manager
from neuravox.api.routers import health, files, jobs, processing, auth, workspace
from neuravox.api.routers import config as config_router
from neuravox.api.middleware.rate_limit import RateLimitMiddleware
from neuravox.api.middleware.request_context import RequestContextMiddleware, get_request_id
from neuravox.api.utils.exceptions import NeuravoxAPIException


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Configure logging first
    configure_logging(component="neuravox.api")
    logger = get_logger("neuravox.api.startup")
    
    # Startup
    logger.info("Starting Neuravox API...")
    
    # Initialize database
    db_manager = get_database_manager()
    await db_manager.create_tables()
    logger.info("Database initialized")
    
    # Ensure workspace directories exist - use project config
    project_config_path = Path(__file__).parent.parent.parent / "config.yaml"
    config = UnifiedConfig(project_config_path if project_config_path.exists() else None)
    config.ensure_workspace_dirs()
    logger.info("Workspace ready", workspace_path=str(config.workspace))
    
    yield
    
    # Shutdown
    logger.info("Shutting down Neuravox API...")
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
    
    # Add request context middleware (first, to set up context)
    app.add_middleware(RequestContextMiddleware)
    
    # Add rate limiting middleware
    app.add_middleware(RateLimitMiddleware, default_rate_limit=60)
    
    # Enhanced exception handlers
    @app.exception_handler(NeuravoxAPIException)
    async def neuravox_exception_handler(request: Request, exc: NeuravoxAPIException):
        logger = get_logger("neuravox.api.error")
        request_id = get_request_id(request)
        
        # Log structured error information
        logger.warning(
            "api_exception",
            error_type=exc.error_type,
            message=exc.message,
            details=exc.details,
            status_code=exc.status_code,
            operation=exc.operation,
            request_id=request_id,
            path=request.url.path,
            method=request.method
        )
        
        # Determine if debug info should be included
        include_debug = os.getenv("NEURAVOX_DEBUG_MODE", "false").lower() == "true"
        
        # Build structured error response
        error_response = {
            "error": exc.to_dict(include_debug=include_debug),
            "request_id": request_id,
            "timestamp": exc.timestamp.isoformat()
        }
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger = get_logger("neuravox.api.error")
        request_id = get_request_id(request)
        
        # Log unexpected errors with full context
        logger.error(
            "unexpected_exception",
            error=str(exc),
            error_type=type(exc).__name__,
            request_id=request_id,
            path=request.url.path,
            method=request.method,
            exc_info=True
        )
        
        # Determine if debug info should be included
        include_debug = os.getenv("NEURAVOX_DEBUG_MODE", "false").lower() == "true"
        
        error_response = {
            "error": {
                "type": "internal_server_error",
                "message": "An unexpected error occurred",
                "details": {"exception": str(exc)} if include_debug else {},
                "retryable": False,
                "timestamp": f"{__import__('datetime').datetime.utcnow().isoformat()}Z"
            },
            "request_id": request_id
        }
        
        return JSONResponse(
            status_code=500,
            content=error_response
        )
    
    # Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(auth.router, prefix="/api/v1", tags=["authentication"])
    app.include_router(files.router, prefix="/api/v1", tags=["files"])
    app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
    app.include_router(processing.router, prefix="/api/v1", tags=["processing"])
    app.include_router(config_router.router, prefix="/api/v1", tags=["configuration"])
    app.include_router(workspace.router, prefix="/api/v1", tags=["workspace"])
    
    # Mount static files for web interface
    web_dir = Path(__file__).parent.parent / "web"
    if web_dir.exists():
        app.mount("/static", StaticFiles(directory=str(web_dir / "static")), name="static")
        
        # Serve the main web interface at root
        @app.get("/")
        async def serve_web_interface():
            """Serve the main web interface"""
            return FileResponse(str(web_dir / "index.html"))
    
    return app


def get_cors_origins() -> list[str]:
    """Get CORS origins from environment"""
    origins_env = os.getenv("API_CORS_ORIGINS", "http://localhost:3000,http://localhost:8000,http://localhost:8080")
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