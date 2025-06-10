"""Logging configuration API for Neuravox"""
import logging
from typing import Optional
from pathlib import Path

# Import from new modular components
from .logging_setup import setup_logging, create_source_logger
from .logging_formats import (
    request_id_var, operation_id_var, job_id_var, task_id_var, user_id_var,
    PrefixFormatter, JSONFormatter, SimpleFormatter,
    get_context_dict, set_context, clear_context
)

# NO MODULE-LEVEL INITIALIZATION - This was causing the circular import!

def configure_logging(
    config: Optional['UnifiedConfig'] = None,
    log_level: str = None,
    log_format: str = None,
    include_context: bool = None,
    log_file: Optional[Path] = None,
    max_file_size_mb: int = None,
    backup_count: int = None,
    **kwargs
) -> None:
    """Configure logging with config object or kwargs
    
    Args:
        config: Optional UnifiedConfig instance
        log_level: Override log level
        log_format: Override log format
        include_context: Override context inclusion
        log_file: Override log file path
        max_file_size_mb: Override max file size
        backup_count: Override backup count
        **kwargs: Additional arguments passed to setup_logging
    """
    if config:
        # Use config object settings
        setup_logging(
            log_format=log_format or config.logging.format,
            log_level=log_level or config.logging.level,
            include_context=include_context if include_context is not None else config.logging.include_context,
            log_file=log_file or (Path(config.logging.file_output) if config.logging.file_output else None),
            max_file_size_mb=max_file_size_mb or config.logging.max_file_size_mb,
            backup_count=backup_count or config.logging.backup_count,
            use_colors=config.logging.use_colors,
            **kwargs
        )
    else:
        # Use provided kwargs or defaults
        setup_logging(
            log_format=log_format or "prefix",
            log_level=log_level or "INFO",
            include_context=include_context if include_context is not None else True,
            log_file=log_file,
            max_file_size_mb=max_file_size_mb or 100,
            backup_count=backup_count or 5,
            **kwargs
        )

# Source-specific logger functions
def get_server_logger() -> logging.Logger:
    """Get server logger for uvicorn/FastAPI server logs"""
    return create_source_logger("server")

def get_app_logger() -> logging.Logger:
    """Get application logger for FastAPI app logs"""
    return create_source_logger("app")

def get_cli_logger() -> logging.Logger:
    """Get CLI logger for command-line interface"""
    return create_source_logger("cli")

def get_req_logger() -> logging.Logger:
    """Get request logger for HTTP request/response logging"""
    return create_source_logger("req")

def get_pipeline_logger() -> logging.Logger:
    """Get pipeline logger for audio processing"""
    return create_source_logger("pipeline")

def get_engine_logger() -> logging.Logger:
    """Get engine logger for transcription engines"""
    return create_source_logger("engine")

def get_job_logger() -> logging.Logger:
    """Get job logger for background jobs"""
    return create_source_logger("job")

def get_db_logger() -> logging.Logger:
    """Get database logger for database operations"""
    return create_source_logger("db")

def get_config_logger() -> logging.Logger:
    """Get config logger for configuration operations"""
    return create_source_logger("config")

def get_logger(name: str = "neuravox") -> logging.Logger:
    """Get a configured logger instance
    
    Args:
        name: Logger name, typically module path
        
    Returns:
        Logger instance configured with appropriate format
    """
    # Extract source from name if possible
    if "." in name:
        parts = name.split(".")
        # Map common module names to sources
        if "api" in parts:
            source = "app"
        elif "cli" in parts:
            source = "cli"
        elif "core" in parts or "pipeline" in parts:
            source = "pipeline"
        elif "transcriber" in parts:
            source = "engine"
        elif "db" in parts:
            source = "db"
        elif "shared.config" in name:
            source = "config"
        else:
            source = parts[-1][:8]  # Take last part, max 8 chars
    else:
        source = "app"
    
    return create_source_logger(source)

# Context management functions
def set_request_context(request_id: str, operation_id: str = None, job_id: str = None):
    """Set context variables for request tracking
    
    Args:
        request_id: Unique request identifier
        operation_id: Optional operation identifier
        job_id: Optional job identifier
    """
    request_id_var.set(request_id)
    if operation_id:
        operation_id_var.set(operation_id)
    if job_id:
        job_id_var.set(job_id)

def clear_request_context():
    """Clear all context variables"""
    clear_context()

class LoggingContextManager:
    """Context manager for setting logging context"""
    
    def __init__(self, request_id: str = None, operation_id: str = None, 
                 job_id: str = None, task_id: str = None, user_id: str = None):
        self.new_context = {}
        if request_id:
            self.new_context["request_id"] = request_id
        if operation_id:
            self.new_context["operation_id"] = operation_id
        if job_id:
            self.new_context["job_id"] = job_id
        if task_id:
            self.new_context["task_id"] = task_id
        if user_id:
            self.new_context["user_id"] = user_id
        
        self.previous_context = {}
    
    def __enter__(self):
        # Save current context
        self.previous_context = get_context_dict()
        
        # Set new context
        set_context(**self.new_context)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Clear context
        clear_context()
        
        # Restore previous context
        if self.previous_context:
            set_context(**self.previous_context)

# Re-export context variables for backward compatibility
__all__ = [
    'configure_logging',
    'get_logger',
    'get_server_logger',
    'get_app_logger', 
    'get_cli_logger',
    'get_req_logger',
    'get_pipeline_logger',
    'get_engine_logger',
    'get_job_logger',
    'get_db_logger',
    'get_config_logger',
    'set_request_context',
    'clear_request_context',
    'LoggingContextManager',
    'request_id_var',
    'operation_id_var',
    'job_id_var',
    'task_id_var',
    'user_id_var'
]