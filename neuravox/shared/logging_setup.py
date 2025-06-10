"""Logging setup without config dependencies"""
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler

# Import will be created in next step
from .logging_formats import PrefixFormatter, JSONFormatter, SimpleFormatter

def setup_logging(
    log_format: str = "prefix",
    log_level: str = "INFO",
    include_context: bool = True,
    log_file: Optional[Path] = None,
    max_file_size_mb: int = 100,
    backup_count: int = 5,
    use_colors: Optional[bool] = None,
    **kwargs
) -> None:
    """Configure logging with provided settings"""
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Configure based on format
    if log_format == "prefix":
        setup_prefix_logging(log_level, include_context, log_file, max_file_size_mb, backup_count, use_colors)
    elif log_format == "json":
        setup_json_logging(log_level, log_file, max_file_size_mb, backup_count)
    else:
        setup_console_logging(log_level, log_file, max_file_size_mb, backup_count)

def setup_prefix_logging(
    log_level: str,
    include_context: bool,
    log_file: Optional[Path],
    max_file_size_mb: int,
    backup_count: int,
    use_colors: Optional[bool] = None
) -> None:
    """Setup prefix-based logging"""
    level = getattr(logging, log_level.upper())
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(PrefixFormatter("main", include_context, use_colors))
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        add_file_handler(root_logger, log_file, level, 
                        PrefixFormatter("main", include_context, use_colors=False),  # No colors in file logs
                        max_file_size_mb, backup_count)

def setup_json_logging(
    log_level: str,
    log_file: Optional[Path],
    max_file_size_mb: int,
    backup_count: int
) -> None:
    """Setup JSON-based logging"""
    level = getattr(logging, log_level.upper())
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(JSONFormatter())
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        add_file_handler(root_logger, log_file, level,
                        JSONFormatter(),
                        max_file_size_mb, backup_count)

def setup_console_logging(
    log_level: str,
    log_file: Optional[Path],
    max_file_size_mb: int,
    backup_count: int
) -> None:
    """Setup simple console logging"""
    level = getattr(logging, log_level.upper())
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(SimpleFormatter())
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        add_file_handler(root_logger, log_file, level,
                        SimpleFormatter(),
                        max_file_size_mb, backup_count)

def add_file_handler(
    logger: logging.Logger,
    log_file: Path,
    level: int,
    formatter: logging.Formatter,
    max_file_size_mb: int,
    backup_count: int
) -> None:
    """Add file handler to logger"""
    # Ensure directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create rotating file handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_file_size_mb * 1024 * 1024,
        backupCount=backup_count
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

def create_source_logger(
    source: str,
    log_level: str = "INFO",
    include_context: bool = True,
    use_colors: Optional[bool] = None
) -> logging.Logger:
    """Create a logger for a specific source"""
    logger_name = f"neuravox.{source}"
    logger = logging.getLogger(logger_name)
    
    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = PrefixFormatter(source, include_context, use_colors)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, log_level.upper()))
        logger.propagate = False
    
    return logger