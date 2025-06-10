"""Configuration data models without dependencies"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

@dataclass
class ProcessingConfig:
    """Audio processing configuration"""
    silence_threshold: float = 0.01
    min_silence_duration: float = 25.0
    sample_rate: int = 16000
    output_format: str = "flac"
    compression_level: int = 8
    normalize: bool = True
    chunk_boundary: str = "simple"

@dataclass
class LoggingConfig:
    """Logging configuration"""
    format: str = "prefix"
    level: str = "INFO"
    include_context: bool = True
    file_output: Optional[str] = None
    max_file_size_mb: int = 100
    backup_count: int = 5
    use_colors: Optional[bool] = None  # None = auto-detect

@dataclass
class ModelConfig:
    """Transcription model configuration"""
    name: str
    provider: str
    model_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    device: Optional[str] = None
    system_prompt: Optional[str] = None
    api_key: Optional[str] = None
    language: str = "en"
    temperature: float = 0.0
    beam_size: int = 5
    best_of: int = 5

@dataclass
class APIConfig:
    """API server configuration"""
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    workers: int = 1
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    max_upload_size_mb: int = 500
    request_timeout: int = 300

@dataclass
class StorageConfig:
    """Storage configuration"""
    database_url: str = "sqlite:///./neuravox.db"
    upload_dir: str = "uploads"
    output_dir: str = "outputs"
    temp_dir: str = "temp"
    max_file_age_days: int = 30
    cleanup_interval_hours: int = 24

@dataclass
class SecurityConfig:
    """Security configuration"""
    require_api_key: bool = False
    api_key_header: str = "X-API-Key"
    allowed_hosts: List[str] = field(default_factory=lambda: ["*"])
    enable_rate_limiting: bool = True
    rate_limit_requests: int = 100
    rate_limit_window_minutes: int = 60