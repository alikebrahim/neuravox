"""
Unified configuration management for Neuravox platform
"""
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
import toml
import os
from pydantic import BaseSettings, Field

class WorkspaceConfig(BaseSettings):
    """Unified workspace configuration"""
    base_path: Path = Field(default=Path.home() / "neuravox")
    input_dir: str = "input"
    processed_dir: str = "processed"
    transcribed_dir: str = "transcribed"
    
    @property
    def input_path(self) -> Path:
        return self.base_path / self.input_dir
    
    @property
    def processed_path(self) -> Path:
        return self.base_path / self.processed_dir
    
    @property
    def transcribed_path(self) -> Path:
        return self.base_path / self.transcribed_dir

    class Config:
        env_prefix = "NEURAVOX_"

class ProcessingConfig(BaseSettings):
    """Audio processing configuration"""
    silence_threshold: float = 0.01
    min_silence_duration: float = 25.0
    min_chunk_duration: float = 5.0
    sample_rate: int = 16000
    output_format: str = "flac"
    compression_level: int = 8
    normalize: bool = True
    chunk_boundary: str = "simple"  # simple or smart
    preserve_timestamps: bool = True

    class Config:
        env_prefix = "NEURAVOX_PROCESSING_"

class TranscriptionConfig(BaseSettings):
    """Transcription configuration"""
    default_model: str = "google-gemini"
    max_concurrent: int = 3
    chunk_processing: bool = True
    combine_chunks: bool = True
    include_timestamps: bool = True
    
    class Config:
        env_prefix = "NEURAVOX_TRANSCRIPTION_"

class APIKeysConfig(BaseSettings):
    """API key management with env var priority"""
    google_api_key: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

class UnifiedConfig:
    """Main configuration manager"""
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("config/default.yaml")
        self.workspace = WorkspaceConfig()
        self.processing = ProcessingConfig()
        self.transcription = TranscriptionConfig()
        self.api_keys = APIKeysConfig()
        
        if self.config_path.exists():
            self._load_config()
    
    def _load_config(self):
        """Load configuration from file"""
        with open(self.config_path) as f:
            data = yaml.safe_load(f)
        
        if "workspace" in data:
            self.workspace = WorkspaceConfig(**data["workspace"])
        if "processing" in data:
            self.processing = ProcessingConfig(**data["processing"])
        if "transcription" in data:
            self.transcription = TranscriptionConfig(**data["transcription"])
    
    def save(self, path: Optional[Path] = None):
        """Save current configuration to file"""
        path = path or self.config_path
        config_data = {
            "workspace": {
                "base_path": str(self.workspace.base_path),
                "input_dir": self.workspace.input_dir,
                "processed_dir": self.workspace.processed_dir,
                "transcribed_dir": self.workspace.transcribed_dir
            },
            "processing": {
                "silence_threshold": self.processing.silence_threshold,
                "min_silence_duration": self.processing.min_silence_duration,
                "min_chunk_duration": self.processing.min_chunk_duration,
                "sample_rate": self.processing.sample_rate,
                "output_format": self.processing.output_format,
                "compression_level": self.processing.compression_level,
                "normalize": self.processing.normalize,
                "chunk_boundary": self.processing.chunk_boundary,
                "preserve_timestamps": self.processing.preserve_timestamps
            },
            "transcription": {
                "default_model": self.transcription.default_model,
                "max_concurrent": self.transcription.max_concurrent,
                "chunk_processing": self.transcription.chunk_processing,
                "combine_chunks": self.transcription.combine_chunks,
                "include_timestamps": self.transcription.include_timestamps
            }
        }
        
        with open(path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)