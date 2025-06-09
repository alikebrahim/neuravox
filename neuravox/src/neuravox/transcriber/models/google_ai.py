import google.genai as genai
from pathlib import Path
import tempfile
import os
from typing import Optional

from .base import AudioTranscriptionModel
from ..prompt_config import prompt_config


class GoogleAIModel(AudioTranscriptionModel):
    """Google AI Studio transcription model."""
    
    def __init__(self, model_id: str = "gemini-2.0-flash-exp", api_key: Optional[str] = None, **kwargs):
        super().__init__(name=f"Google {model_id}", config=kwargs)
        self.model_id = model_id
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            self.model = self.client.models
        else:
            self.client = None
            self.model = None
    
    def is_available(self) -> bool:
        """Check if the model is available and properly configured."""
        return self.api_key is not None and self.model is not None
    
    async def transcribe(self, audio_path: Path) -> str:
        """
        Transcribe audio file using Google AI Studio.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Transcribed text
        """
        if not self.is_available():
            raise ValueError("Google AI model is not properly configured. Please set GOOGLE_API_KEY.")
        
        if not self.validate_audio_file(audio_path):
            raise ValueError(f"Invalid audio file: {audio_path}")
        
        try:
            # Upload the audio file
            audio_file = self.client.files.upload(file=str(audio_path))
            
            # Get system prompt from configuration
            # First check if custom prompt is provided in model config
            custom_prompt = self.config.get("system_prompt")
            if custom_prompt:
                prompt = custom_prompt
            else:
                # Use prompt from TOML config based on provider
                prompt = prompt_config.get_prompt("google")
                
            # If no configured prompt, use default hardcoded prompt
            if not prompt:
                prompt = """Please transcribe the audio in this file. Provide only the transcribed text without any additional commentary, explanations, or formatting. 
If there are multiple speakers, indicate speaker changes with [Speaker 1], [Speaker 2], etc.
Ensure the transcription is accurate and includes proper punctuation."""
            
            # Generate transcription
            response = await self._generate_async(prompt, audio_file)
            
            # Clean up uploaded file
            self.client.files.delete(name=audio_file.name)
            
            return response.text.strip()
            
        except Exception as e:
            raise RuntimeError(f"Google AI transcription failed: {e}")
    
    async def _generate_async(self, prompt: str, audio_file):
        """Generate response asynchronously."""
        try:
            # Note: google-genai doesn't have async support yet, so we'll use sync
            # In a real implementation, you might want to use asyncio.to_thread
            import asyncio
            return await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_id,
                contents=[prompt, audio_file]
            )
        except Exception as e:
            raise RuntimeError(f"Failed to generate content: {e}")
    
    def get_supported_formats(self) -> list[str]:
        """Get list of supported audio formats."""
        return [
            ".mp3", ".wav", ".aiff", ".aac", ".ogg", ".flac", ".m4a"
        ]