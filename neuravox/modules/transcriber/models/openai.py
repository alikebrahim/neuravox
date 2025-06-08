from openai import AsyncOpenAI
from pathlib import Path
import os
from typing import Optional

from .base import AudioTranscriptionModel
from ..prompt_config import prompt_config


class OpenAIModel(AudioTranscriptionModel):
    """OpenAI Whisper transcription model."""
    
    def __init__(self, model_id: str = "whisper-1", api_key: Optional[str] = None, **kwargs):
        super().__init__(name=f"OpenAI {model_id}", config=kwargs)
        self.model_id = model_id
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key)
        else:
            self.client = None
    
    def is_available(self) -> bool:
        """Check if the model is available and properly configured."""
        return self.api_key is not None and self.client is not None
    
    async def transcribe(self, audio_path: Path) -> str:
        """
        Transcribe audio file using OpenAI Whisper.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Transcribed text
        """
        if not self.is_available():
            raise ValueError("OpenAI model is not properly configured. Please set OPENAI_API_KEY.")
        
        if not self.validate_audio_file(audio_path):
            raise ValueError(f"Invalid audio file: {audio_path}")
        
        try:
            # Get system prompt
            custom_prompt = self.config.get("system_prompt")
            if not custom_prompt:
                custom_prompt = prompt_config.get_prompt("openai")
            
            # For OpenAI Whisper, the prompt parameter guides the style
            # If no prompt configured, Whisper will use its default behavior
            whisper_prompt = self.config.get("prompt", custom_prompt)
            
            # Prepare parameters from config
            params = {
                "model": self.model_id,
                "response_format": self.config.get("response_format", "text"),
                "language": self.config.get("language"),  # Optional: specify language
                "prompt": whisper_prompt if whisper_prompt else None,  # Optional: guide the model
                "temperature": self.config.get("temperature", 0.0)  # Deterministic by default
            }
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            # Open and transcribe the audio file
            with open(audio_path, "rb") as audio_file:
                transcript = await self.client.audio.transcriptions.create(
                    file=audio_file,
                    **params
                )
            
            # Handle different response formats
            if isinstance(transcript, str):
                return transcript.strip()
            else:
                return transcript.text.strip()
                
        except Exception as e:
            raise RuntimeError(f"OpenAI transcription failed: {e}")
    
    def get_supported_formats(self) -> list[str]:
        """Get list of supported audio formats for OpenAI Whisper."""
        return [
            ".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"
        ]
    
    def get_max_file_size(self) -> int:
        """Get maximum file size in bytes (25MB for OpenAI Whisper)."""
        return 25 * 1024 * 1024  # 25MB
    
    def validate_audio_file(self, audio_path: Path) -> bool:
        """Validate audio file for OpenAI Whisper requirements."""
        if not super().validate_audio_file(audio_path):
            return False
        
        # Check file size
        file_size = audio_path.stat().st_size
        if file_size > self.get_max_file_size():
            return False
        
        # Check format
        if audio_path.suffix.lower() not in self.get_supported_formats():
            return False
        
        return True