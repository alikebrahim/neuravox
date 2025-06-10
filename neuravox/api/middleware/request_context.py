"""Request context middleware for API request tracking"""

import uuid
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from neuravox.shared.logging_config import get_logger, set_request_context, clear_request_context


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID tracking and logging context"""
    
    def __init__(self, app, logger_name: str = "neuravox.api"):
        super().__init__(app)
        self.logger = get_logger(logger_name)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Set logging context
        set_request_context(request_id)
        
        # Start timing
        start_time = time.time()
        
        # Log request start
        self.logger.info(
            "request_started",
            method=request.method,
            url=str(request.url),
            path=request.url.path,
            query_params=dict(request.query_params),
            user_agent=request.headers.get("user-agent"),
            client_ip=getattr(request.client, 'host', None) if request.client else None,
            request_id=request_id
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log successful request completion
            self.logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_seconds=round(duration, 3),
                request_id=request_id
            )
            
            # Add request ID to response headers for debugging
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate duration for failed request
            duration = time.time() - start_time
            
            # Log request failure
            self.logger.error(
                "request_failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=round(duration, 3),
                request_id=request_id,
                exc_info=True
            )
            
            # Re-raise exception to be handled by FastAPI
            raise
            
        finally:
            # Clear logging context
            clear_request_context()


def get_request_id(request: Request) -> str:
    """Get request ID from request state
    
    Args:
        request: FastAPI request object
        
    Returns:
        Request ID string
    """
    return getattr(request.state, 'request_id', 'unknown')