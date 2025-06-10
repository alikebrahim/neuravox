"""Pure configuration loading without dependencies"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

def load_config_data(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load raw configuration data from file or defaults"""
    # Determine config path
    if config_path:
        path = Path(config_path)
    elif env_config := os.getenv("NEURAVOX_CONFIG"):
        path = Path(env_config)
    else:
        path = Path.home() / ".neuravox" / "config.yaml"
    
    # Load from file if exists
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}

def get_env_overrides() -> Dict[str, Any]:
    """Get environment variable overrides"""
    overrides = {}
    
    # Workspace override
    if workspace := os.getenv("NEURAVOX_WORKSPACE"):
        overrides["workspace"] = workspace
    
    # Logging overrides
    if log_level := os.getenv("NEURAVOX_LOG_LEVEL"):
        overrides.setdefault("logging", {})["level"] = log_level
    
    if log_format := os.getenv("NEURAVOX_LOG_FORMAT"):
        overrides.setdefault("logging", {})["format"] = log_format
    
    if log_context := os.getenv("NEURAVOX_LOG_CONTEXT"):
        overrides.setdefault("logging", {})["include_context"] = log_context.lower() == "true"
    
    if log_file := os.getenv("NEURAVOX_LOG_FILE"):
        overrides.setdefault("logging", {})["file_output"] = log_file
    
    if use_colors := os.getenv("NEURAVOX_LOG_COLORS"):
        overrides.setdefault("logging", {})["use_colors"] = use_colors.lower() in ("true", "1", "yes")
    
    # Model overrides
    if model_provider := os.getenv("NEURAVOX_MODEL_PROVIDER"):
        overrides.setdefault("model", {})["provider"] = model_provider
    
    if model_name := os.getenv("NEURAVOX_MODEL_NAME"):
        overrides.setdefault("model", {})["name"] = model_name
    
    if api_key := os.getenv("NEURAVOX_API_KEY"):
        overrides.setdefault("model", {})["api_key"] = api_key
    
    # API overrides
    if api_enabled := os.getenv("NEURAVOX_API_ENABLED"):
        overrides.setdefault("api", {})["enabled"] = api_enabled.lower() == "true"
    
    if api_host := os.getenv("NEURAVOX_API_HOST"):
        overrides.setdefault("api", {})["host"] = api_host
    
    if api_port := os.getenv("NEURAVOX_API_PORT"):
        overrides.setdefault("api", {})["port"] = int(api_port)
    
    return overrides