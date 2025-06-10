"""Centralized logging configuration for Neuravox"""

import os
import sys
import logging
import logging.config
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any
from contextvars import ContextVar

import structlog
from pythonjsonlogger import jsonlogger


# Context variables for request/operation tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
operation_id_var: ContextVar[Optional[str]] = ContextVar('operation_id', default=None)
job_id_var: ContextVar[Optional[str]] = ContextVar('job_id', default=None)


class PrefixFormatter(logging.Formatter):
    """Custom formatter with source prefixes and center-padding"""
    
    def __init__(self, source: str, include_context: bool = True):
        self.source = source.center(8)  # Center-pad to 8 chars
        self.include_context = include_context
        super().__init__()
    
    def format(self, record):
        level = record.levelname.center(5)  # Center-pad to 5 chars
        message = record.getMessage()
        
        # Add context if available and enabled
        context_parts = []
        if self.include_context:
            if hasattr(record, 'request_id') and record.request_id:
                context_parts.append(f"request_id={record.request_id}")
            if hasattr(record, 'operation_id') and record.operation_id:
                context_parts.append(f"operation_id={record.operation_id}")
            if hasattr(record, 'job_id') and record.job_id:
                context_parts.append(f"job_id={record.job_id}")
            
            # Add any extra context from record
            for key, value in getattr(record, 'extra_context', {}).items():
                context_parts.append(f"{key}={value}")
        
        context = f" {' '.join(context_parts)}" if context_parts else ""
        
        return f"[{self.source}]-[{level}]: {message}{context}"


def add_context_processor(logger, method_name, event_dict):
    """Add context variables to log entries"""
    if request_id := request_id_var.get():
        event_dict["request_id"] = request_id
    if operation_id := operation_id_var.get():
        event_dict["operation_id"] = operation_id
    if job_id := job_id_var.get():
        event_dict["job_id"] = job_id
    return event_dict


def get_log_level() -> str:
    """Get the configured log level from environment or config"""
    # Environment variable takes precedence
    if level := os.getenv("NEURAVOX_LOG_LEVEL"):
        return level.upper()
    
    # Try to get from config if available
    try:
        from neuravox.shared.config import UnifiedConfig
        config = UnifiedConfig(validate=False)
        return config.logging.level.upper()
    except Exception:
        # Fallback to default
        return "INFO"


def get_log_format() -> str:
    """Get the configured log format from environment or config"""
    # Environment variable takes precedence
    if format_env := os.getenv("NEURAVOX_LOG_FORMAT"):
        return format_env.lower()
    
    # Try to get from config if available
    try:
        from neuravox.shared.config import UnifiedConfig
        config = UnifiedConfig(validate=False)
        return config.logging.format.lower()
    except Exception:
        # Fallback to default
        return "prefix"


def should_include_context() -> bool:
    """Check if context should be included in logs"""
    # Environment variable takes precedence
    if context_env := os.getenv("NEURAVOX_LOG_CONTEXT"):
        return context_env.lower() == "true"
    
    # Try to get from config if available
    try:
        from neuravox.shared.config import UnifiedConfig
        config = UnifiedConfig(validate=False)
        return config.logging.include_context
    except Exception:
        # Fallback to default
        return True


def get_log_file() -> Optional[Path]:
    """Get log file path from environment or config"""
    # Environment variable takes precedence
    if file_env := os.getenv("NEURAVOX_LOG_FILE"):
        return Path(file_env)
    
    # Try to get from config if available
    try:
        from neuravox.shared.config import UnifiedConfig
        config = UnifiedConfig(validate=False)
        if config.logging.file_output:
            return Path(config.logging.file_output)
    except Exception:
        pass
    
    return None


def get_source_logger(source: str, include_context: bool = None) -> logging.Logger:
    """Get a logger configured for specific source with prefix formatting
    
    Args:
        source: Source identifier (server, app, cli, req, etc.)
        include_context: Whether to include context info (default: from env)
        
    Returns:
        Configured logger instance
    """
    if include_context is None:
        include_context = should_include_context()
    
    logger_name = f"neuravox.{source}"
    logger = logging.getLogger(logger_name)
    
    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = PrefixFormatter(source, include_context)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, get_log_level()))
        logger.propagate = False  # Prevent duplicate logs
    
    # Add context injection
    original_handle = logger.handle
    
    def handle_with_context(record):
        # Inject context variables into record
        if request_id := request_id_var.get():
            record.request_id = request_id
        if operation_id := operation_id_var.get():
            record.operation_id = operation_id
        if job_id := job_id_var.get():
            record.job_id = job_id
        
        original_handle(record)
    
    logger.handle = handle_with_context
    return logger


# Convenience functions for common sources
def get_server_logger() -> logging.Logger:
    """Get server logger for uvicorn/FastAPI server logs"""
    return get_source_logger("server")


def get_app_logger() -> logging.Logger:
    """Get application logger for FastAPI app logs"""
    return get_source_logger("app")


def get_cli_logger() -> logging.Logger:
    """Get CLI logger for command-line interface"""
    return get_source_logger("cli")


def get_req_logger() -> logging.Logger:
    """Get request logger for HTTP request/response logging"""
    return get_source_logger("req")


def get_pipeline_logger() -> logging.Logger:
    """Get pipeline logger for audio processing"""
    return get_source_logger("pipeline")


def get_engine_logger() -> logging.Logger:
    """Get engine logger for transcription engines"""
    return get_source_logger("engine")


def get_job_logger() -> logging.Logger:
    """Get job logger for background jobs"""
    return get_source_logger("job")


def get_db_logger() -> logging.Logger:
    """Get database logger for database operations"""
    return get_source_logger("db")


def get_config_logger() -> logging.Logger:
    """Get config logger for configuration operations"""
    return get_source_logger("config")


def configure_logging(
    log_level: str = None,
    log_file: Optional[Path] = None,
    log_format: str = None,
    component: str = "neuravox"
) -> None:
    """Configure logging for Neuravox components with format selection
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        log_format: Format type (prefix, json, console) - default: prefix
        component: Component name for logger identification
    """
    
    # Get configuration from environment, config file, or defaults
    log_level = log_level or get_log_level()
    log_format = log_format or get_log_format()
    log_file = log_file or get_log_file()
    
    # Clear any existing handlers to prevent duplicates
    logging.getLogger().handlers.clear()
    
    if log_format == "prefix":
        # Use prefix-based logging (new default)
        configure_prefix_logging(log_level, log_file)
    elif log_format == "json":
        # Use JSON structured logging (legacy)
        configure_json_logging(log_level, log_file)
    else:
        # Use console logging (development)
        configure_console_logging(log_level, log_file)


def configure_prefix_logging(log_level: str, log_file: Optional[Path] = None) -> None:
    """Configure prefix-based logging format"""
    # Basic logging setup with minimal console output
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(message)s",
        handlers=[]  # We'll add handlers explicitly
    )
    
    # Configure file logging if specified
    if log_file:
        configure_file_logging(log_file, log_level, use_prefix=True)


def configure_json_logging(log_level: str, log_file: Optional[Path] = None) -> None:
    """Configure JSON structured logging (legacy format)"""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level)
    )
    
    # Configure structlog processors for JSON output
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_context_processor,
        structlog.processors.JSONRenderer()
    ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    if log_file:
        configure_file_logging(log_file, log_level, use_prefix=False)


def configure_console_logging(log_level: str, log_file: Optional[Path] = None) -> None:
    """Configure console logging with colors (development)"""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level)
    )
    
    # Configure structlog processors for colored console output
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_context_processor,
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(colors=True)
    ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    if log_file:
        configure_file_logging(log_file, log_level, use_prefix=False)


def configure_file_logging(log_file: Path, log_level: str, use_prefix: bool = True) -> None:
    """Configure file logging with rotation"""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create file handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=5
    )
    
    if use_prefix:
        # Use prefix format for file logging too
        formatter = PrefixFormatter("file", include_context=True)
    else:
        # Use JSON format for structured file logging
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
    
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, log_level))
    
    # Add to root logger
    logging.getLogger().addHandler(file_handler)


def get_logger(name: str = "neuravox"):
    """Get a configured logger instance
    
    Args:
        name: Logger name, typically module path
        
    Returns:
        Logger instance (type depends on configured format)
    """
    log_format = get_log_format()
    
    if log_format == "prefix":
        # For prefix format, return standard logger
        # Extract source from name if possible
        if "." in name:
            source = name.split(".")[-1]
        else:
            source = "app"
        return get_source_logger(source)
    else:
        # For json/console formats, return structlog logger
        return structlog.get_logger(name)


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
    request_id_var.set(None)
    operation_id_var.set(None)
    job_id_var.set(None)


class LoggingContextManager:
    """Context manager for setting logging context"""
    
    def __init__(self, request_id: str = None, operation_id: str = None, job_id: str = None):
        self.request_id = request_id
        self.operation_id = operation_id
        self.job_id = job_id
        self.previous_request_id = None
        self.previous_operation_id = None
        self.previous_job_id = None
    
    def __enter__(self):
        # Save previous context
        self.previous_request_id = request_id_var.get()
        self.previous_operation_id = operation_id_var.get()
        self.previous_job_id = job_id_var.get()
        
        # Set new context
        if self.request_id:
            request_id_var.set(self.request_id)
        if self.operation_id:
            operation_id_var.set(self.operation_id)
        if self.job_id:
            job_id_var.set(self.job_id)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore previous context
        request_id_var.set(self.previous_request_id)
        operation_id_var.set(self.previous_operation_id)
        job_id_var.set(self.previous_job_id)


# Initialize logging on module import
# Only configure if we're using prefix format (default)
# Other formats will be configured explicitly
log_format = get_log_format()
if log_format == "prefix" and not logging.getLogger().handlers:
    configure_logging()
elif log_format != "prefix" and not structlog.is_configured():
    configure_logging()