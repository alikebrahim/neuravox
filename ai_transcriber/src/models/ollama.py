import requests
import base64
from pathlib import Path
from typing import Optional, Dict, Any
import json

from .base import AudioTranscriptionModel
from ..prompt_config import prompt_config


class OllamaModel(AudioTranscriptionModel):
    """Ollama local model for audio transcription."""
    
    def __init__(self, model_id: str = "phi4", api_url: str = "http://localhost:11434", **kwargs):
        super().__init__(name=f"Ollama {model_id}", config=kwargs)
        self.model_id = model_id
        self.api_url = api_url.rstrip("/")
        
    def is_available(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            # Check if Ollama is running
            response = requests.get(f"{self.api_url}/api/version", timeout=5)
            if response.status_code != 200:
                return False
            
            # Check if the model is available
            response = requests.post(
                f"{self.api_url}/api/show",
                json={"name": self.model_id},
                timeout=10
            )
            return response.status_code == 200
            
        except Exception:
            return False
    
    async def transcribe(self, audio_path: Path) -> str:
        """
        Transcribe audio file using Ollama local model.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Transcribed text
        """
        if not self.is_available():
            raise ValueError(f"Ollama model '{self.model_id}' is not available. Make sure Ollama is running and the model is installed.")
        
        if not self.validate_audio_file(audio_path):
            raise ValueError(f"Invalid audio file: {audio_path}")
        
        try:
            # Convert audio to base64
            audio_base64 = self._encode_audio_to_base64(audio_path)
            
            # Get system prompt from configuration
            custom_prompt = self.config.get("system_prompt")
            if custom_prompt:
                prompt = custom_prompt
            else:
                # Use prompt from TOML config based on provider
                prompt = prompt_config.get_prompt("ollama")
                
            # If no configured prompt, use default hardcoded prompt
            if not prompt:
                prompt = "Please transcribe the audio in the provided file. Provide only the transcribed text without any additional commentary or formatting."
            
            # Prepare the request
            payload = {
                "model": self.model_id,
                "prompt": prompt,
                "images": [audio_base64],
                "stream": False,
                "options": {
                    "temperature": self.config.get("temperature", 0.1),
                    "top_p": self.config.get("top_p", 0.9),
                    "top_k": self.config.get("top_k", 40)
                }
            }
            
            # Make the request
            response = requests.post(
                f"{self.api_url}/api/generate",
                json=payload,
                timeout=300  # 5 minutes timeout for transcription
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Ollama API error: {response.status_code} - {response.text}")
            
            result = response.json()
            transcription = result.get("response", "").strip()
            
            if not transcription:
                raise RuntimeError("Empty transcription received from Ollama")
            
            return transcription
            
        except Exception as e:
            raise RuntimeError(f"Ollama transcription failed: {e}")
    
    def _encode_audio_to_base64(self, audio_path: Path) -> str:
        """Encode audio file to base64 string."""
        try:
            with open(audio_path, "rb") as audio_file:
                audio_data = audio_file.read()
                return base64.b64encode(audio_data).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to encode audio file: {e}")
    
    def get_supported_formats(self) -> list[str]:
        """Get list of supported audio formats."""
        # Note: This depends on the specific model capabilities
        # Phi-4 and other multimodal models typically support common formats
        return [
            ".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac"
        ]
    
    def pull_model(self) -> bool:
        """Pull/download the model if not available."""
        try:
            response = requests.post(
                f"{self.api_url}/api/pull",
                json={"name": self.model_id},
                timeout=600  # 10 minutes for model download
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def list_available_models(self) -> list[str]:
        """List all available models in Ollama."""
        try:
            response = requests.get(f"{self.api_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except Exception:
            return []
    
    def get_model_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the model."""
        try:
            response = requests.post(
                f"{self.api_url}/api/show",
                json={"name": self.model_id},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None