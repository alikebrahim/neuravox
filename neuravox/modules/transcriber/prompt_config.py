"""Prompt configuration management for audio transcription."""

import toml
from pathlib import Path
from typing import Dict, Any, Optional
import re


class PromptConfig:
    """Manages system prompts for transcription models."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("config/prompts.toml")
        self.prompts: Dict[str, Any] = {}
        self.load_prompts()
    
    def load_prompts(self):
        """Load prompts from TOML configuration file."""
        if self.config_path.exists():
            try:
                self.prompts = toml.load(self.config_path)
            except Exception as e:
                print(f"Warning: Failed to load prompts from {self.config_path}: {e}")
                self.prompts = self._get_default_prompts()
        else:
            self.prompts = self._get_default_prompts()
            # Create the default config file
            self.save_prompts()
    
    def save_prompts(self):
        """Save current prompts to TOML file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                toml.dump(self.prompts, f)
        except Exception as e:
            print(f"Warning: Failed to save prompts to {self.config_path}: {e}")
    
    def get_prompt(self, provider: str, prompt_type: Optional[str] = None) -> str:
        """
        Get system prompt for a specific provider.
        
        Args:
            provider: The model provider (google, openai, ollama)
            prompt_type: Optional specific prompt type (meeting, technical, etc.)
            
        Returns:
            The system prompt string
        """
        # If specific prompt type requested
        if prompt_type and prompt_type in self.prompts:
            return self.prompts[prompt_type].get("system_prompt", "")
        
        # Try provider-specific prompt
        if provider in self.prompts:
            return self.prompts[provider].get("system_prompt", "")
        
        # Fall back to default
        return self.prompts.get("default", {}).get("system_prompt", "")
    
    def get_prompt_for_context(self, provider: str, context: str) -> str:
        """
        Get system prompt based on context analysis.
        
        Args:
            provider: The model provider
            context: Context string (filename, description, etc.)
            
        Returns:
            The most appropriate system prompt
        """
        # Check prompt selection rules
        rules = self.prompts.get("prompt_selection", {}).get("rules", [])
        
        for rule in rules:
            if "pattern" in rule:
                pattern = rule["pattern"]
                if re.search(pattern, context, re.IGNORECASE):
                    prompt_type = rule.get("prompt", "default")
                    return self.get_prompt(provider, prompt_type)
        
        # Default to provider-specific or default prompt
        return self.get_prompt(provider)
    
    def get_options(self) -> Dict[str, Any]:
        """Get additional transcription options."""
        return self.prompts.get("options", {})
    
    def update_prompt(self, key: str, prompt: str):
        """Update a specific prompt."""
        if key not in self.prompts:
            self.prompts[key] = {}
        self.prompts[key]["system_prompt"] = prompt
        self.save_prompts()
    
    def list_available_prompts(self) -> list[str]:
        """List all available prompt keys."""
        return [k for k in self.prompts.keys() 
                if isinstance(self.prompts[k], dict) and "system_prompt" in self.prompts[k]]
    
    def _get_default_prompts(self) -> Dict[str, Any]:
        """Get default prompts if config file is missing."""
        return {
            "default": {
                "system_prompt": """You are a professional audio transcription assistant. Your task is to provide an accurate, complete transcription of the audio content.

Guidelines:
1. Transcribe all spoken words exactly as heard
2. Use proper punctuation and capitalization
3. Indicate speaker changes with [Speaker 1], [Speaker 2], etc.
4. Note significant non-verbal audio cues in square brackets
5. Mark unclear parts as [inaudible]
6. Maintain the original language
7. Do not add commentary or summaries

Provide only the transcription."""
            },
            "google": {
                "system_prompt": """Please provide a complete and accurate transcription of the audio file. Include proper punctuation, indicate speaker changes, and note any unclear segments as [inaudible]. Output only the transcription text."""
            },
            "openai": {
                "system_prompt": """Transcribe the audio with proper formatting, punctuation, and speaker identification where applicable."""
            },
            "ollama": {
                "system_prompt": """Task: Transcribe the audio file completely and accurately. Include all spoken words, proper punctuation, and speaker labels. Mark unclear audio as [inaudible]."""
            },
            "options": {
                "include_fillers": True,
                "include_non_verbal": True,
                "auto_timestamps": True,
                "timestamp_threshold_minutes": 10
            }
        }


# Global prompt config instance
prompt_config = PromptConfig()