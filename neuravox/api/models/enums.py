"""API enumeration types"""

from enum import Enum


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Job type enumeration"""
    PROCESS = "process"
    TRANSCRIBE = "transcribe"
    PIPELINE = "pipeline"


class FileRole(str, Enum):
    """File role enumeration"""
    INPUT = "input"
    OUTPUT = "output"
    INTERMEDIATE = "intermediate"


class ModelProvider(str, Enum):
    """Model provider enumeration"""
    GOOGLE = "google"
    OPENAI = "openai"
    WHISPER_LOCAL = "whisper-local"