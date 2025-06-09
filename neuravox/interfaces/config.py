"""Configuration management interfaces"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List


class IConfigManager(ABC):
    """Interface for configuration management"""
    
    @abstractmethod
    def get_model(self, model_key: str) -> Optional[Any]:
        """
        Get model configuration by key
        
        Args:
            model_key: Model identifier
            
        Returns:
            Model configuration object or None if not found
        """
        pass
    
    @abstractmethod
    def list_models(self) -> List[str]:
        """
        List available model keys
        
        Returns:
            List of available model identifiers
        """
        pass
    
    @abstractmethod
    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a provider
        
        Args:
            provider: Provider name (e.g., 'google', 'openai')
            
        Returns:
            API key string or None if not found
        """
        pass
    
    @abstractmethod
    def ensure_workspace_dirs(self):
        """Create workspace directories if they don't exist"""
        pass
    
    @property
    @abstractmethod
    def workspace(self) -> Path:
        """
        Get workspace path
        
        Returns:
            Path to the workspace directory
        """
        pass
    
    @property
    @abstractmethod
    def input_path(self) -> Path:
        """Get input directory path"""
        pass
    
    @property
    @abstractmethod
    def processed_path(self) -> Path:
        """Get processed directory path"""
        pass
    
    @property
    @abstractmethod
    def transcribed_path(self) -> Path:
        """Get transcribed directory path"""
        pass