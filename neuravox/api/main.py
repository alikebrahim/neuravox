"""Main FastAPI application for Neuravox API"""

import os
import sys
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from neuravox.shared.config import UnifiedConfig
from neuravox.shared.logging_config import configure_logging, get_app_logger, get_config_logger, get_db_logger, get_logger
from neuravox.shared.logging_formats import PrefixFormatter
from neuravox.db.database import get_database_manager
from neuravox.api.routers import health, files, jobs, processing, auth, workspace
from neuravox.api.routers import config as config_router
from neuravox.api.middleware.rate_limit import RateLimitMiddleware
from neuravox.api.middleware.request_context import RequestContextMiddleware, get_request_id
from neuravox.api.utils.exceptions import NeuravoxAPIException


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Initialize configuration first
    project_config_path = Path(__file__).parent.parent.parent / "config.yaml"
    config = UnifiedConfig(project_config_path if project_config_path.exists() else None)
    
    # Configure logging with the config object
    configure_logging(config)
    
    # Get loggers
    app_logger = get_app_logger()
    config_logger = get_config_logger()
    db_logger = get_db_logger()
    
    # Startup
    app_logger.info("Starting Neuravox API...")
    config_logger.info(f"Configuration loaded from {str(project_config_path) if project_config_path.exists() else 'default'}")
    
    # Initialize database
    db_manager = get_database_manager()
    await db_manager.create_tables()
    db_logger.info("Database initialized")
    
    # Ensure workspace directories exist
    config.ensure_workspace_dirs()
    config_logger.info(f"Workspace ready at {str(config.workspace)}")
    
    # Store config in app state for reuse
    app.state.config = config
    
    yield
    
    # Shutdown
    app_logger.info("Shutting down Neuravox API...")
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
    
    # Configuration will be loaded in lifespan manager and stored in app.state
    # This prevents duplicate configuration loading
    
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
        error_logger = get_logger("neuravox.api.error")
        request_id = get_request_id(request)
        
        # Log structured error information
        error_logger.warning(
            f"API exception: {exc.message}",
            extra={
                'extra_context': {
                    'error_type': exc.error_type,
                    'status_code': exc.status_code,
                    'operation': exc.operation,
                    'path': request.url.path,
                    'method': request.method
                }
            }
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
        error_logger = get_logger("neuravox.api.error")
        request_id = get_request_id(request)
        
        # Log unexpected errors with full context
        error_logger.error(
            f"Unexpected exception: {str(exc)}",
            extra={
                'extra_context': {
                    'error_type': type(exc).__name__,
                    'path': request.url.path,
                    'method': request.method
                }
            },
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


def configure_uvicorn_logging():
    """Configure uvicorn to use prefix-based logging"""
    # Configure uvicorn loggers to use our prefix format
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_error = logging.getLogger("uvicorn.error")
    
    # Clear existing handlers
    uvicorn_logger.handlers.clear()
    uvicorn_access.handlers.clear() 
    uvicorn_error.handlers.clear()
    
    # Add prefix handlers
    server_handler = logging.StreamHandler(sys.stdout)
    server_formatter = PrefixFormatter("server")
    server_handler.setFormatter(server_formatter)
    
    uvicorn_logger.addHandler(server_handler)
    uvicorn_access.addHandler(server_handler)
    uvicorn_error.addHandler(server_handler)
    
    # Set log levels
    log_level = os.getenv("NEURAVOX_LOG_LEVEL", "INFO").upper()
    uvicorn_logger.setLevel(getattr(logging, log_level))
    uvicorn_access.setLevel(getattr(logging, log_level))
    uvicorn_error.setLevel(getattr(logging, log_level))
    
    # Prevent propagation to avoid duplicates
    uvicorn_logger.propagate = False
    uvicorn_access.propagate = False
    uvicorn_error.propagate = False


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    workers: int = 1,
    reload: bool = False,
    config_path: Optional[Path] = None
):
    """Run the API server with prefix-based logging"""
    # Configure uvicorn logging first
    configure_uvicorn_logging()
    
    app = create_app(config_path)
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        workers=workers if not reload else 1,  # reload only works with 1 worker
        reload=reload,
        log_config=None,  # Disable uvicorn's log config
        access_log=False  # We handle access logging in middleware
    )


if __name__ == "__main__":
    # For development
    run_server(reload=True)