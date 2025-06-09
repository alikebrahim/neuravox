from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path
import librosa
import numpy as np


class AudioTranscriptionModel(ABC):
    """Abstract base class for audio transcription models."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
    
    @abstractmethod
    async def transcribe(self, audio_path: Path) -> str:
        """
        Transcribe audio file to text.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Transcribed text
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the model is available and properly configured."""
        pass
    
    def preprocess_audio(self, audio_path: Path) -> tuple[np.ndarray, int]:
        """
        Load and preprocess audio file using librosa.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Tuple of (audio_data, sample_rate)
        """
        try:
            audio_data, sample_rate = librosa.load(str(audio_path), sr=None)
            return audio_data, sample_rate
        except Exception as e:
            raise ValueError(f"Failed to load audio file {audio_path}: {e}")
    
    def get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration in seconds."""
        try:
            duration = librosa.get_duration(path=str(audio_path))
            return duration
        except Exception as e:
            raise ValueError(f"Failed to get audio duration for {audio_path}: {e}")
    
    def validate_audio_file(self, audio_path: Path) -> bool:
        """Validate that the audio file can be processed."""
        if not audio_path.exists():
            return False
        
        try:
            # Try to load first few seconds to validate format
            librosa.load(str(audio_path), sr=None, duration=1.0)
            return True
        except Exception:
            return False
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
    
    def __repr__(self) -> str:
        return self.__str__()