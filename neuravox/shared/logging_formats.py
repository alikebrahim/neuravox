"""Logging formatters without dependencies"""
import logging
import json
import os
import sys
from contextvars import ContextVar
from typing import Optional, Dict, Any
from datetime import datetime

# Context variables for tracking IDs across async operations
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
operation_id_var: ContextVar[Optional[str]] = ContextVar('operation_id', default=None)
job_id_var: ContextVar[Optional[str]] = ContextVar('job_id', default=None)
task_id_var: ContextVar[Optional[str]] = ContextVar('task_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)

# ANSI color codes
class Colors:
    """ANSI color codes for terminal output"""
    # Reset
    RESET = '\033[0m'
    
    # Regular colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright/bold colors
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    
    # Bold
    BOLD = '\033[1m'

# Color mapping for log levels
LEVEL_COLORS = {
    'DEBUG': Colors.CYAN,
    'INFO': Colors.GREEN,
    'WARNING': Colors.YELLOW,
    'ERROR': Colors.RED,
    'CRITICAL': Colors.BRIGHT_RED + Colors.BOLD,
}

def supports_color() -> bool:
    """Check if the terminal supports color output"""
    # Check if colors are explicitly disabled
    if os.getenv('NO_COLOR') or os.getenv('NEURAVOX_NO_COLOR'):
        return False
    
    # Check if forced
    if os.getenv('FORCE_COLOR') or os.getenv('NEURAVOX_FORCE_COLOR'):
        return True
    
    # Check if stdout is a tty
    if not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
        return False
    
    # Check terminal type
    term = os.getenv('TERM', '')
    if term == 'dumb':
        return False
    
    # Check platform
    if sys.platform == 'win32':
        # Modern Windows 10+ terminals support ANSI codes
        return True
    
    return True

class PrefixFormatter(logging.Formatter):
    """Custom formatter with source prefixes, optional context, and color support"""
    
    def __init__(self, source: str, include_context: bool = True, use_colors: bool = None):
        self.source = source.ljust(8)  # Left-pad to 8 chars (longest: "pipeline")
        self.include_context = include_context
        self.use_colors = use_colors if use_colors is not None else supports_color()
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        # Format level with proper padding (left-padded to 8 chars, longest: "CRITICAL")
        level = record.levelname.ljust(8)
        
        # Get the base message
        message = record.getMessage()
        
        # Build context parts if enabled
        context_parts = []
        if self.include_context:
            # Add any context variables that are set
            if request_id := request_id_var.get():
                context_parts.append(f"request_id={request_id}")
            if operation_id := operation_id_var.get():
                context_parts.append(f"operation_id={operation_id}")
            if job_id := job_id_var.get():
                context_parts.append(f"job_id={job_id}")
            if task_id := task_id_var.get():
                context_parts.append(f"task_id={task_id}")
            if user_id := user_id_var.get():
                context_parts.append(f"user_id={user_id}")
            
            # Add any extra context from the record
            if hasattr(record, 'context') and record.context:
                for key, value in record.context.items():
                    context_parts.append(f"{key}={value}")
        
        # Format the final message
        context = f" {' '.join(context_parts)}" if context_parts else ""
        
        # Apply colors if enabled
        if self.use_colors:
            color = LEVEL_COLORS.get(record.levelname, '')
            # Color both the source and level based on the log level
            colored_source = f"{color}[{self.source}]{Colors.RESET}"
            colored_level = f"{color}[{level}]{Colors.RESET}"
            return f"{colored_source}-{colored_level}: {message}{context}"
        else:
            return f"[{self.source}]-[{level}]: {message}{context}"

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Build the log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add context variables if they exist
        context = {}
        if request_id := request_id_var.get():
            context["request_id"] = request_id
        if operation_id := operation_id_var.get():
            context["operation_id"] = operation_id
        if job_id := job_id_var.get():
            context["job_id"] = job_id
        if task_id := task_id_var.get():
            context["task_id"] = task_id
        if user_id := user_id_var.get():
            context["user_id"] = user_id
        
        if context:
            log_entry["context"] = context
        
        # Add any extra fields from the record
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

class SimpleFormatter(logging.Formatter):
    """Simple console formatter"""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

def get_context_dict() -> Dict[str, Any]:
    """Get current context as a dictionary"""
    context = {}
    
    if request_id := request_id_var.get():
        context["request_id"] = request_id
    if operation_id := operation_id_var.get():
        context["operation_id"] = operation_id
    if job_id := job_id_var.get():
        context["job_id"] = job_id
    if task_id := task_id_var.get():
        context["task_id"] = task_id
    if user_id := user_id_var.get():
        context["user_id"] = user_id
    
    return context

def set_context(**kwargs) -> None:
    """Set multiple context variables at once"""
    if "request_id" in kwargs:
        request_id_var.set(kwargs["request_id"])
    if "operation_id" in kwargs:
        operation_id_var.set(kwargs["operation_id"])
    if "job_id" in kwargs:
        job_id_var.set(kwargs["job_id"])
    if "task_id" in kwargs:
        task_id_var.set(kwargs["task_id"])
    if "user_id" in kwargs:
        user_id_var.set(kwargs["user_id"])

def clear_context() -> None:
    """Clear all context variables"""
    request_id_var.set(None)
    operation_id_var.set(None)
    job_id_var.set(None)
    task_id_var.set(None)
    user_id_var.set(None)