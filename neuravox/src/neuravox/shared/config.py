"""
Simplified configuration management for Neuravox
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class ProcessingConfig:
    """Audio processing configuration with defaults"""
    silence_threshold: float = 0.01
    min_silence_duration: float = 25.0
    sample_rate: int = 16000
    output_format: str = "flac"
    compression_level: int = 8
    normalize: bool = True
    chunk_boundary: str = "simple"


@dataclass
class TranscriptionConfig:
    """Transcription configuration with defaults"""
    default_model: str = "google-gemini"
    max_concurrent: int = 3
    chunk_processing: bool = True
    combine_chunks: bool = True
    include_timestamps: bool = True


@dataclass
class ModelConfig:
    """Model configuration"""
    name: str
    provider: str
    model_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    device: Optional[str] = None  # For local models


class UnifiedConfig:
    """Simplified configuration manager for personal tool"""
    
    def __init__(self, config_path: Optional[Path] = None):
        # 1. Determine config path
        if config_path:
            self.config_path = Path(config_path)
        elif env_config := os.getenv("NEURAVOX_CONFIG"):
            self.config_path = Path(env_config)
        else:
            # Single, predictable location
            self.config_path = Path.home() / ".neuravox" / "config.yaml"
        
        # 2. Load defaults
        self._load_defaults()
        
        # 3. Override with user config if exists
        if self.config_path.exists():
            self._merge_user_config()
        
        # 4. Apply environment overrides
        self._apply_env_overrides()
    
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
        try:
            with open(self.config_path) as f:
                data = yaml.safe_load(f)
            
            # Workspace
            if "workspace" in data:
                self.workspace = Path(data["workspace"]).expanduser()
            
            # Processing
            if "processing" in data:
                for key, value in data["processing"].items():
                    if hasattr(self.processing, key):
                        setattr(self.processing, key, value)
            
            # Transcription
            if "transcription" in data:
                for key, value in data["transcription"].items():
                    if hasattr(self.transcription, key):
                        setattr(self.transcription, key, value)
            
            # Models
            if "models" in data:
                for model_key, model_data in data["models"].items():
                    if model_key in self.models:
                        # Update existing model
                        for key, value in model_data.items():
                            if hasattr(self.models[model_key], key):
                                setattr(self.models[model_key], key, value)
                    else:
                        # Add new model
                        self.models[model_key] = ModelConfig(**model_data)
        
        except Exception as e:
            print(f"Warning: Failed to load config from {self.config_path}: {e}")
    
    def _apply_env_overrides(self):
        """Apply minimal environment variable overrides"""
        # Workspace override
        if workspace_env := os.getenv("NEURAVOX_WORKSPACE"):
            self.workspace = Path(workspace_env).expanduser()
    
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
        for dir_path in [self.input_path, self.processed_path, self.transcribed_path]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a provider from environment"""
        if provider == "google":
            return os.getenv("GOOGLE_API_KEY")
        elif provider == "openai":
            return os.getenv("OPENAI_API_KEY")
        return None


# For backward compatibility - remove deprecated attributes gradually
class WorkspaceConfig:
    """Deprecated - for backward compatibility only"""
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.input_dir = "input"
        self.processed_dir = "processed"
        self.transcribed_dir = "transcribed"
    
    @property
    def input_path(self) -> Path:
        return self.base_path / self.input_dir
    
    @property
    def processed_path(self) -> Path:
        return self.base_path / self.processed_dir
    
    @property
    def transcribed_path(self) -> Path:
        return self.base_path / self.transcribed_dir


# Global config instance for backward compatibility
config = UnifiedConfig()