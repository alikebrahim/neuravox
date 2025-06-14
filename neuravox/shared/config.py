"""
Unified configuration API for Neuravox
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

# Import from new modular components
from .config_loader import load_config_data, get_env_overrides
from .config_models import (
    ProcessingConfig, LoggingConfig, ModelConfig, 
    APIConfig, StorageConfig, SecurityConfig
)
from .logging_setup import create_source_logger
from neuravox.api.utils.exceptions import ConfigurationError


@dataclass
class TranscriptionConfig:
    """Transcription configuration with defaults"""
    default_model: str = "google-gemini"
    max_concurrent: int = 3
    chunk_processing: bool = True
    combine_chunks: bool = True
    include_timestamps: bool = True


class UnifiedConfig:
    """Configuration manager facade"""
    
    def __init__(self, config_path: Optional[Path] = None, validate: bool = True):
        self.validation_errors = []
        self.validation_warnings = []
        
        # Load configuration data
        self._raw_config = load_config_data(config_path)
        self._env_overrides = get_env_overrides()
        
        # Store config path for reference
        if config_path:
            self.config_path = Path(config_path)
        elif env_config := os.getenv("NEURAVOX_CONFIG"):
            self.config_path = Path(env_config)
        else:
            self.config_path = Path.home() / ".neuravox" / "config.yaml"
        
        # Initialize components
        self._load_defaults()
        self._merge_user_config()
        self._apply_env_overrides()
        
        # Lazy logger initialization
        self._logger = None
        
        if validate:
            self._validate_configuration()
    
    @property
    def logger(self):
        """Lazy logger initialization"""
        if self._logger is None:
            self._logger = create_source_logger(
                "config",
                self.logging.level,
                self.logging.include_context
            )
        return self._logger
    
    def _load_defaults(self):
        """Load hardcoded defaults"""
        # Workspace
        self.workspace = Path.home() / ".neuravox" / "workspace"
        
        # Processing defaults
        self.processing = ProcessingConfig()
        
        # Transcription defaults
        self.transcription = TranscriptionConfig()
        
        # Default models
        self.models = self._get_default_models()
        
        # Logging defaults
        self.logging = LoggingConfig()
        
        # API defaults
        self.api = APIConfig()
        
        # Storage defaults
        self.storage = StorageConfig()
        
        # Security defaults
        self.security = SecurityConfig()
    
    def _get_default_models(self) -> Dict[str, ModelConfig]:
        """Get default model configurations"""
        return {
            "google-gemini": ModelConfig(
                name="Google Gemini Flash",
                provider="google",
                model_id="gemini-2.0-flash-exp",
                parameters={"temperature": 0.1}
            ),
            "openai-whisper": ModelConfig(
                name="OpenAI Whisper",
                provider="openai",
                model_id="whisper-1",
                parameters={"response_format": "text"}
            ),
            "whisper-base": ModelConfig(
                name="Whisper Base (Local)",
                provider="whisper-local",
                model_id="base",
                device=None,
                parameters={"language": None}
            ),
            "whisper-turbo": ModelConfig(
                name="Whisper Turbo (Local)",
                provider="whisper-local",
                model_id="turbo",
                device=None,
                parameters={"language": None}
            )
        }
    
    def _merge_user_config(self):
        """Merge user config file with defaults"""
        if not self._raw_config:
            return
        
        try:
            # Workspace
            if "workspace" in self._raw_config:
                self.workspace = Path(self._raw_config["workspace"]).expanduser()
            
            # Processing
            if "processing" in self._raw_config:
                for key, value in self._raw_config["processing"].items():
                    if hasattr(self.processing, key):
                        setattr(self.processing, key, value)
            
            # Transcription
            if "transcription" in self._raw_config:
                for key, value in self._raw_config["transcription"].items():
                    if hasattr(self.transcription, key):
                        setattr(self.transcription, key, value)
            
            # Models
            if "models" in self._raw_config:
                for model_key, model_data in self._raw_config["models"].items():
                    if model_key in self.models:
                        # Update existing model
                        for key, value in model_data.items():
                            if hasattr(self.models[model_key], key):
                                setattr(self.models[model_key], key, value)
                    else:
                        # Add new model
                        self.models[model_key] = ModelConfig(**model_data)
            
            # Logging
            if "logging" in self._raw_config:
                for key, value in self._raw_config["logging"].items():
                    if hasattr(self.logging, key):
                        setattr(self.logging, key, value)
            
            # API
            if "api" in self._raw_config:
                for key, value in self._raw_config["api"].items():
                    if hasattr(self.api, key):
                        setattr(self.api, key, value)
            
            # Storage
            if "storage" in self._raw_config:
                for key, value in self._raw_config["storage"].items():
                    if hasattr(self.storage, key):
                        setattr(self.storage, key, value)
            
            # Security
            if "security" in self._raw_config:
                for key, value in self._raw_config["security"].items():
                    if hasattr(self.security, key):
                        setattr(self.security, key, value)
            
            # Prompts - set system_prompt for all models
            if "prompts" in self._raw_config and "system_prompt" in self._raw_config["prompts"]:
                system_prompt = self._raw_config["prompts"]["system_prompt"]
                for model in self.models.values():
                    if not model.system_prompt:  # Only set if not already specified
                        model.system_prompt = system_prompt
        
        except Exception as e:
            error_msg = f"Failed to merge config from {self.config_path}: {e}"
            self.validation_warnings.append(error_msg)
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        if not self._env_overrides:
            return
        
        # Workspace override
        if "workspace" in self._env_overrides:
            self.workspace = Path(self._env_overrides["workspace"]).expanduser()
        
        # Logging overrides
        if "logging" in self._env_overrides:
            for key, value in self._env_overrides["logging"].items():
                if hasattr(self.logging, key):
                    setattr(self.logging, key, value)
        
        # Model overrides
        if "model" in self._env_overrides:
            model_overrides = self._env_overrides["model"]
            # Apply to default model if specified
            if "provider" in model_overrides or "name" in model_overrides:
                default_model_key = self.transcription.default_model
                if default_model_key in self.models:
                    for key, value in model_overrides.items():
                        if hasattr(self.models[default_model_key], key):
                            setattr(self.models[default_model_key], key, value)
        
        # API overrides
        if "api" in self._env_overrides:
            for key, value in self._env_overrides["api"].items():
                if hasattr(self.api, key):
                    setattr(self.api, key, value)
    
    # Convenience properties for backward compatibility
    @property
    def input_path(self) -> Path:
        """Get input directory path"""
        return self.workspace / "input"
    
    @property
    def processed_path(self) -> Path:
        """Get processed directory path"""
        return self.workspace / "processed"
    
    @property
    def transcribed_path(self) -> Path:
        """Get transcribed directory path"""
        return self.workspace / "transcribed"
    
    def get_model(self, model_key: str) -> Optional[ModelConfig]:
        """Get model configuration by key"""
        return self.models.get(model_key)
    
    def list_models(self) -> List[str]:
        """List available model keys"""
        return list(self.models.keys())
    
    def ensure_workspace_dirs(self):
        """Create workspace directories if they don't exist"""
        try:
            for dir_path in [self.input_path, self.processed_path, self.transcribed_path]:
                dir_path.mkdir(parents=True, exist_ok=True)
                self.logger.debug("workspace_dir_created", path=str(dir_path))
        except Exception as e:
            error_msg = f"Failed to create workspace directories: {e}"
            self.logger.error("workspace_creation_failed", error=str(e), workspace=str(self.workspace))
            raise ConfigurationError(error_msg, details={"workspace": str(self.workspace)})
    
    def _validate_configuration(self):
        """Validate configuration settings and dependencies"""
        if self._logger:
            self.logger.info("config_validation_started")
        
        # Validate workspace
        self._validate_workspace()
        
        # Validate processing configuration
        self._validate_processing_config()
        
        # Validate transcription configuration
        self._validate_transcription_config()
        
        # Validate models
        self._validate_models()
        
        # Check for critical errors
        if self.validation_errors:
            error_summary = "; ".join(self.validation_errors)
            if self._logger:
                self.logger.error(
                    "config_validation_failed",
                    error_count=len(self.validation_errors),
                    warning_count=len(self.validation_warnings),
                    errors=self.validation_errors
                )
            raise ConfigurationError(
                f"Configuration validation failed: {error_summary}",
                details={
                    "errors": self.validation_errors,
                    "warnings": self.validation_warnings
                }
            )
        
        # Log warnings
        if self.validation_warnings and self._logger:
            self.logger.warning(
                "config_validation_warnings",
                warning_count=len(self.validation_warnings),
                warnings=self.validation_warnings
            )
        
        if self._logger:
            self.logger.info(
                "config_validation_completed",
                warning_count=len(self.validation_warnings)
            )
    
    def _validate_workspace(self):
        """Validate workspace configuration"""
        if not self.workspace:
            self.validation_errors.append("Workspace path not configured")
            return
        
        # Check if workspace is accessible
        try:
            workspace_path = Path(self.workspace)
            if workspace_path.exists():
                if not workspace_path.is_dir():
                    self.validation_errors.append(f"Workspace path exists but is not a directory: {workspace_path}")
                elif not os.access(workspace_path, os.W_OK):
                    self.validation_errors.append(f"Workspace directory is not writable: {workspace_path}")
            else:
                # Try to create parent directories
                try:
                    workspace_path.parent.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    self.validation_errors.append(f"Cannot create workspace parent directories: {workspace_path.parent}")
        except Exception as e:
            self.validation_errors.append(f"Invalid workspace path: {e}")
    
    def _validate_processing_config(self):
        """Validate processing configuration"""
        if not hasattr(self, 'processing') or not self.processing:
            self.validation_errors.append("Processing configuration missing")
            return
        
        # Validate silence threshold
        if not (0.001 <= self.processing.silence_threshold <= 1.0):
            self.validation_errors.append(f"Invalid silence_threshold: {self.processing.silence_threshold} (must be 0.001-1.0)")
        
        # Validate min silence duration
        if not (0.1 <= self.processing.min_silence_duration <= 300.0):
            self.validation_errors.append(f"Invalid min_silence_duration: {self.processing.min_silence_duration} (must be 0.1-300.0)")
        
        # Validate sample rate
        valid_rates = [8000, 16000, 22050, 44100, 48000]
        if self.processing.sample_rate not in valid_rates:
            self.validation_warnings.append(f"Unusual sample_rate: {self.processing.sample_rate} (recommended: {valid_rates})")
        
        # Validate output format
        valid_formats = ["flac", "wav", "mp3"]
        if self.processing.output_format not in valid_formats:
            self.validation_errors.append(f"Invalid output_format: {self.processing.output_format} (must be one of: {valid_formats})")
    
    def _validate_transcription_config(self):
        """Validate transcription configuration"""
        if not hasattr(self, 'transcription') or not self.transcription:
            self.validation_errors.append("Transcription configuration missing")
            return
        
        # Validate max concurrent
        if not (1 <= self.transcription.max_concurrent <= 10):
            self.validation_errors.append(f"Invalid max_concurrent: {self.transcription.max_concurrent} (must be 1-10)")
        
        # Validate default model exists
        if self.transcription.default_model not in self.models:
            self.validation_errors.append(f"Default transcription model not found: {self.transcription.default_model}")
    
    def _validate_models(self):
        """Validate model configurations"""
        if not hasattr(self, 'models') or not self.models:
            self.validation_errors.append("No models configured")
            return
        
        for model_name, model_config in self.models.items():
            # Validate required fields
            if not model_config.provider:
                self.validation_errors.append(f"Model {model_name} missing provider")
            
            if not model_config.model_id:
                self.validation_errors.append(f"Model {model_name} missing model_id")
            
            # Validate provider-specific requirements
            if model_config.provider == "google-ai":
                api_key = os.getenv("GOOGLE_AI_API_KEY")
                if not api_key:
                    self.validation_warnings.append(f"Model {model_name} (Google AI) missing API key (GOOGLE_AI_API_KEY)")
            
            elif model_config.provider == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    self.validation_warnings.append(f"Model {model_name} (OpenAI) missing API key (OPENAI_API_KEY)")
            
            elif model_config.provider == "whisper-local":
                # Check if device is available for local models
                if model_config.device == "cuda":
                    try:
                        import torch
                        if not torch.cuda.is_available():
                            self.validation_warnings.append(f"Model {model_name} configured for CUDA but CUDA not available")
                    except ImportError:
                        self.validation_warnings.append(f"Model {model_name} requires PyTorch but it's not installed")
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get configuration validation summary"""
        return {
            "valid": len(self.validation_errors) == 0,
            "errors": self.validation_errors,
            "warnings": self.validation_warnings,
            "config_path": str(self.config_path),
            "workspace": str(self.workspace)
        }
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a provider from environment"""
        if provider == "google":
            return os.getenv("GOOGLE_API_KEY")
        elif provider == "openai":
            return os.getenv("OPENAI_API_KEY")
        return None