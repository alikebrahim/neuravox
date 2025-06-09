"""
Unified configuration management for Neuravox platform
"""
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml
import toml
import os
import json
from pydantic import Field, BaseModel, field_validator
from pydantic_settings import BaseSettings

class WorkspaceConfig(BaseSettings):
    """Unified workspace configuration"""
    base_path: Path = Field(default=Path.home() / ".neuravox" / "workspace")
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

    model_config = {
        "env_prefix": "NEURAVOX_"
    }

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

    model_config = {
        "env_prefix": "NEURAVOX_PROCESSING_"
    }

class TranscriptionConfig(BaseSettings):
    """Transcription configuration"""
    default_model: str = "google-gemini"
    max_concurrent: int = 3
    chunk_processing: bool = True
    combine_chunks: bool = True
    include_timestamps: bool = True
    
    model_config = {
        "env_prefix": "NEURAVOX_TRANSCRIPTION_"
    }

class APIKeysConfig(BaseSettings):
    """API key management with env var priority"""
    google_api_key: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }

class ModelConfig(BaseModel):
    """Configuration for a specific transcription model."""
    name: str
    provider: str  # 'google', 'openai', 'whisper-local'
    model_id: str
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    device: Optional[str] = None  # For local models: 'cuda', 'cpu', or None for auto
    parameters: Dict[str, Any] = Field(default_factory=dict)
    system_prompt: Optional[str] = None  # Custom system prompt override
    
    @field_validator('provider')
    def validate_provider(cls, v):
        if v not in ['google', 'openai', 'whisper-local']:
            raise ValueError('Provider must be one of: google, openai, whisper-local')
        return v

class ProjectConfig(BaseModel):
    """Configuration for a transcription project."""
    name: str
    output_dir: Path
    model: str
    audio_files: List[Path] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {
        "arbitrary_types_allowed": True
    }

class UnifiedConfig:
    """Main configuration manager"""
    def __init__(self, config_path: Optional[Path] = None):
        # Check multiple locations for config file
        if config_path:
            self.config_path = config_path
        else:
            # Check for NEURAVOX_CONFIG environment variable first
            env_config = os.getenv("NEURAVOX_CONFIG")
            if env_config and Path(env_config).exists():
                self.config_path = Path(env_config)
            else:
                # Use fixed location for personal tool
                neuravox_home = Path.home() / ".neuravox"
                user_config = neuravox_home / "config" / "user.yaml"
                default_config = neuravox_home / "config" / "default.yaml"
                
                if user_config.exists():
                    self.config_path = user_config
                elif default_config.exists():
                    self.config_path = default_config
                else:
                    # Fallback to relative path (for development)
                    self.config_path = Path("config/default.yaml")
        
        self.workspace = WorkspaceConfig()
        self.processing = ProcessingConfig()
        self.transcription = TranscriptionConfig()
        self.api_keys = APIKeysConfig()
        self.models: Dict[str, ModelConfig] = self._get_default_models()
        self.recent_projects: List[str] = []
        
        if self.config_path.exists():
            self._load_config()
    
    def _load_config(self):
        """Load configuration from file"""
        with open(self.config_path) as f:
            data = yaml.safe_load(f)
        
        if "workspace" in data:
            # Expand home directory in base_path if present
            workspace_data = data["workspace"].copy()
            if "base_path" in workspace_data:
                workspace_data["base_path"] = Path(workspace_data["base_path"]).expanduser()
            self.workspace = WorkspaceConfig(**workspace_data)
        if "processing" in data:
            self.processing = ProcessingConfig(**data["processing"])
        if "transcription" in data:
            self.transcription = TranscriptionConfig(**data["transcription"])
        if "api_keys" in data:
            # Map YAML keys to expected field names
            if "google_gemini" in data["api_keys"]:
                self.api_keys.google_api_key = data["api_keys"]["google_gemini"]
            if "openai" in data["api_keys"]:
                self.api_keys.openai_api_key = data["api_keys"]["openai"]
        if "models" in data:
            self.models = {}
            for key, model_data in data["models"].items():
                # Handle API key from config or environment
                if "api_key" not in model_data or model_data["api_key"] is None:
                    if model_data.get("provider") == "google":
                        model_data["api_key"] = self.api_keys.google_api_key
                    elif model_data.get("provider") == "openai":
                        model_data["api_key"] = self.api_keys.openai_api_key
                self.models[key] = ModelConfig(**model_data)
        if "recent_projects" in data:
            self.recent_projects = data["recent_projects"]
    
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
    
    def _get_default_models(self) -> Dict[str, ModelConfig]:
        """Get default model configurations"""
        return {
            "google-gemini": ModelConfig(
                name="Google Gemini Flash",
                provider="google",
                model_id="gemini-2.0-flash-exp",
                api_key=os.getenv("GOOGLE_API_KEY"),
                parameters={"temperature": 0.1}
            ),
            "openai-whisper": ModelConfig(
                name="OpenAI Whisper",
                provider="openai",
                model_id="whisper-1",
                api_key=os.getenv("OPENAI_API_KEY"),
                parameters={"response_format": "text"}
            ),
            "whisper-base": ModelConfig(
                name="Whisper Base (Local)",
                provider="whisper-local",
                model_id="base",
                device=None,  # Auto-detect
                parameters={"language": None}  # Auto-detect language
            ),
            "whisper-turbo": ModelConfig(
                name="Whisper Turbo (Local)",
                provider="whisper-local",
                model_id="turbo",
                device=None,  # Auto-detect
                parameters={"language": None}  # Auto-detect language
            )
        }
    
    def add_model(self, model_config: ModelConfig):
        """Add a new model configuration."""
        self.models[model_config.name.lower().replace(" ", "-")] = model_config
        self.save()
    
    def get_model(self, model_key: str) -> Optional[ModelConfig]:
        """Get model configuration by key."""
        return self.models.get(model_key)
    
    def list_models(self) -> List[str]:
        """List available model keys."""
        return list(self.models.keys())
    
    def add_recent_project(self, project_name: str):
        """Add a project to recent projects list."""
        if project_name in self.recent_projects:
            self.recent_projects.remove(project_name)
        self.recent_projects.insert(0, project_name)
        self.recent_projects = self.recent_projects[:10]
        self.save()
    
    def save_project_config(self, project: ProjectConfig):
        """Save project configuration to file."""
        project_dir = self.workspace.transcribed_path / project.name
        project_dir.mkdir(parents=True, exist_ok=True)
        
        project_config_path = project_dir / "project_config.json"
        try:
            config_dict = project.model_dump()
            # Convert Path objects to strings for JSON serialization
            self._convert_paths_to_strings(config_dict)
            
            with open(project_config_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save project config: {e}")
    
    def load_project_config(self, project_name: str) -> Optional[ProjectConfig]:
        """Load project configuration from file."""
        project_config_path = self.workspace.transcribed_path / project_name / "project_config.json"
        
        if project_config_path.exists():
            try:
                with open(project_config_path, 'r') as f:
                    data = json.load(f)
                return ProjectConfig(**data)
            except Exception as e:
                print(f"Warning: Failed to load project config: {e}")
        
        return None
    
    def _convert_paths_to_strings(self, obj):
        """Recursively convert Path objects to strings in a dictionary."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, Path):
                    obj[key] = str(value)
                elif isinstance(value, (dict, list)):
                    self._convert_paths_to_strings(value)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, Path):
                    obj[i] = str(item)
                elif isinstance(item, (dict, list)):
                    self._convert_paths_to_strings(item)


# Global config instance for backward compatibility
config = UnifiedConfig()