"""Centralized logging configuration for Neuravox"""

import os
import sys
import logging
import logging.config
from pathlib import Path
from typing import Optional
from contextvars import ContextVar

import structlog
from pythonjsonlogger import jsonlogger


# Context variables for request/operation tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
operation_id_var: ContextVar[Optional[str]] = ContextVar('operation_id', default=None)
job_id_var: ContextVar[Optional[str]] = ContextVar('job_id', default=None)


def add_context_processor(logger, method_name, event_dict):
    """Add context variables to log entries"""
    if request_id := request_id_var.get():
        event_dict["request_id"] = request_id
    if operation_id := operation_id_var.get():
        event_dict["operation_id"] = operation_id
    if job_id := job_id_var.get():
        event_dict["job_id"] = job_id
    return event_dict


def configure_logging(
    log_level: str = None,
    log_file: Optional[Path] = None,
    json_format: bool = None,
    component: str = "neuravox"
) -> None:
    """Configure structured logging for Neuravox components
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        json_format: Whether to use JSON format (default: True for production)
        component: Component name for logger identification
    """
    
    # Get configuration from environment or defaults
    log_level = log_level or os.getenv("NEURAVOX_LOG_LEVEL", "INFO")
    json_format = json_format if json_format is not None else os.getenv("NEURAVOX_LOG_JSON", "true").lower() == "true"
    log_file = log_file or (Path(os.getenv("NEURAVOX_LOG_FILE", "")) if os.getenv("NEURAVOX_LOG_FILE") else None)
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )
    
    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_context_processor,
    ]
    
    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend([
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=True)
        ])
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure file logging if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=5
        )
        
        if json_format:
            formatter = jsonlogger.JsonFormatter(
                '%(asctime)s %(name)s %(levelname)s %(message)s'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        
        # Add to root logger
        logging.getLogger().addHandler(file_handler)


def get_logger(name: str = "neuravox") -> structlog.BoundLogger:
    """Get a configured logger instance
    
    Args:
        name: Logger name, typically module path
        
    Returns:
        Configured structlog logger
    """
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
if not structlog.is_configured():
    configure_logging()