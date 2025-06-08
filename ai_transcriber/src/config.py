from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import os


class ModelConfig(BaseModel):
    """Configuration for a specific transcription model."""
    name: str
    provider: str  # 'google', 'openai', 'ollama'
    model_id: str
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    system_prompt: Optional[str] = None  # Custom system prompt override
    
    @validator('provider')
    def validate_provider(cls, v):
        if v not in ['google', 'openai', 'ollama']:
            raise ValueError('Provider must be one of: google, openai, ollama')
        return v


class ProjectConfig(BaseModel):
    """Configuration for a transcription project."""
    name: str
    output_dir: Path
    model: str
    audio_files: List[Path] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True


class GlobalConfig(BaseModel):
    """Global application configuration."""
    input_dir: Path = Path("input")
    output_dir: Path = Path("output")
    config_dir: Path = Path("config")
    default_model: str = "google-gemini"
    models: Dict[str, ModelConfig] = Field(default_factory=dict)
    recent_projects: List[str] = Field(default_factory=list, max_items=10)
    
    class Config:
        arbitrary_types_allowed = True
    
    def add_recent_project(self, project_name: str):
        """Add a project to recent projects list."""
        if project_name in self.recent_projects:
            self.recent_projects.remove(project_name)
        self.recent_projects.insert(0, project_name)
        self.recent_projects = self.recent_projects[:10]


class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("config/app_config.json")
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config: Optional[GlobalConfig] = None
    
    @property
    def config(self) -> GlobalConfig:
        """Get the current configuration, loading if needed."""
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def load_config(self) -> GlobalConfig:
        """Load configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                return GlobalConfig(**data)
            except Exception as e:
                print(f"Warning: Failed to load config from {self.config_path}: {e}")
                print("Using default configuration.")
        
        return self._create_default_config()
    
    def save_config(self):
        """Save current configuration to file."""
        if self._config is None:
            return
        
        try:
            # Convert Path objects to strings for JSON serialization
            config_dict = self._config.dict()
            self._convert_paths_to_strings(config_dict)
            
            with open(self.config_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save config to {self.config_path}: {e}")
    
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
    
    def _create_default_config(self) -> GlobalConfig:
        """Create default configuration with example models."""
        default_models = {
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
            "ollama-phi4": ModelConfig(
                name="Phi-4 Multimodal",
                provider="ollama",
                model_id="phi4",
                api_url="http://localhost:11434",
                parameters={"temperature": 0.1}
            )
        }
        
        return GlobalConfig(
            default_model="google-gemini",
            models=default_models
        )
    
    def add_model(self, model_config: ModelConfig):
        """Add a new model configuration."""
        self.config.models[model_config.name.lower().replace(" ", "-")] = model_config
        self.save_config()
    
    def get_model(self, model_key: str) -> Optional[ModelConfig]:
        """Get model configuration by key."""
        return self.config.models.get(model_key)
    
    def list_models(self) -> List[str]:
        """List available model keys."""
        return list(self.config.models.keys())
    
    def save_project_config(self, project: ProjectConfig):
        """Save project configuration to file."""
        project_dir = self.config.output_dir / project.name
        project_dir.mkdir(parents=True, exist_ok=True)
        
        project_config_path = project_dir / "project_config.json"
        try:
            config_dict = project.dict()
            self._convert_paths_to_strings(config_dict)
            
            with open(project_config_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save project config: {e}")
    
    def load_project_config(self, project_name: str) -> Optional[ProjectConfig]:
        """Load project configuration from file."""
        project_config_path = self.config.output_dir / project_name / "project_config.json"
        
        if project_config_path.exists():
            try:
                with open(project_config_path, 'r') as f:
                    data = json.load(f)
                return ProjectConfig(**data)
            except Exception as e:
                print(f"Warning: Failed to load project config: {e}")
        
        return None


# Global config manager instance
config_manager = ConfigManager()