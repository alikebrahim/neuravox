import whisper
from pathlib import Path
from typing import Optional, Dict, Any
import torch
import warnings
import os

from .base import AudioTranscriptionModel


class LocalWhisperModel(AudioTranscriptionModel):
    """Local Whisper model for offline audio transcription."""
    
    # Model sizes and their parameters
    AVAILABLE_MODELS = {
        "tiny": "39M parameters - Fastest, lowest accuracy",
        "tiny.en": "39M parameters - English-only, slightly better for English",
        "base": "74M parameters - Fast, good accuracy",
        "base.en": "74M parameters - English-only, better for English",
        "small": "244M parameters - Good balance of speed and accuracy",
        "small.en": "244M parameters - English-only, better for English",
        "medium": "769M parameters - High accuracy, slower",
        "medium.en": "769M parameters - English-only, better for English",
        "large": "1550M parameters - Best accuracy, slowest",
        "large-v2": "1550M parameters - Improved large model",
        "large-v3": "1550M parameters - Latest large model",
        "turbo": "809M parameters - Optimized for speed"
    }
    
    def __init__(self, model_id: str = "base", device: Optional[str] = None, **kwargs):
        """
        Initialize local Whisper model.
        
        Args:
            model_id: Model size (tiny, base, small, medium, large, turbo)
            device: Device to use (cuda, cpu, or None for auto-detect)
            **kwargs: Additional configuration options
        """
        # Extract just the model size from IDs like "whisper-base"
        if model_id.startswith("whisper-"):
            model_id = model_id.replace("whisper-", "")
            
        if model_id not in self.AVAILABLE_MODELS:
            raise ValueError(f"Invalid model: {model_id}. Available: {list(self.AVAILABLE_MODELS.keys())}")
            
        super().__init__(name=f"Whisper {model_id} (Local)", config=kwargs)
        self.model_id = model_id
        self.device = device
        self.model = None
        self._model_loaded = False
        
        # Suppress warnings about FP16 on CPU
        warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")
    
    def _load_model(self):
        """Load the Whisper model if not already loaded."""
        if not self._model_loaded:
            try:
                # Auto-detect device if not specified
                if self.device is None:
                    self.device = "cuda" if torch.cuda.is_available() else "cpu"
                
                # Download and load model
                download_root = self.config.get("download_root", None)
                self.model = whisper.load_model(
                    self.model_id,
                    device=self.device,
                    download_root=download_root
                )
                self._model_loaded = True
                
            except Exception as e:
                raise RuntimeError(f"Failed to load Whisper model '{self.model_id}': {e}")
    
    def is_available(self) -> bool:
        """Check if the model is available and can be loaded."""
        try:
            # Check if ffmpeg is available (required for audio processing)
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, 
                                  text=True,
                                  check=False)
            if result.returncode != 0:
                return False
            
            # Try to import whisper
            import whisper
            return True
            
        except (ImportError, FileNotFoundError):
            return False
    
    async def transcribe(self, audio_path: Path) -> str:
        """
        Transcribe audio file using local Whisper model.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Transcribed text
        """
        if not self.is_available():
            raise ValueError("Whisper is not properly installed. Please install with: pip install openai-whisper")
        
        if not self.validate_audio_file(audio_path):
            raise ValueError(f"Invalid audio file: {audio_path}")
        
        # Load model if not already loaded
        self._load_model()
        
        try:
            # Prepare transcription options
            options = {
                "language": self.config.get("language", None),  # Auto-detect if not specified
                "task": self.config.get("task", "transcribe"),  # or "translate" 
                "temperature": self.config.get("temperature", 0.0),
                "compression_ratio_threshold": self.config.get("compression_ratio_threshold", 2.4),
                "logprob_threshold": self.config.get("logprob_threshold", -1.0),
                "no_speech_threshold": self.config.get("no_speech_threshold", 0.6),
                "condition_on_previous_text": self.config.get("condition_on_previous_text", True),
                "initial_prompt": self.config.get("initial_prompt", None),
                "word_timestamps": self.config.get("word_timestamps", False),
                "verbose": self.config.get("verbose", False)
            }
            
            # Remove None values
            options = {k: v for k, v in options.items() if v is not None}
            
            # Transcribe the audio
            result = self.model.transcribe(str(audio_path), **options)
            
            # Extract text from result
            text = result["text"].strip()
            
            # Add language info if detected
            if "language" in result and result["language"] != self.config.get("language"):
                detected_lang = result["language"]
                if self.config.get("include_language_info", False):
                    text = f"[Detected language: {detected_lang}]\n\n{text}"
            
            return text
            
        except Exception as e:
            raise RuntimeError(f"Whisper transcription failed: {e}")
    
    def get_supported_formats(self) -> list[str]:
        """Get list of supported audio formats."""
        # Whisper uses ffmpeg, so it supports many formats
        return [
            ".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm",
            ".flac", ".aac", ".ogg", ".opus", ".wma", ".amr"
        ]
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            "model_id": self.model_id,
            "description": self.AVAILABLE_MODELS.get(self.model_id, "Unknown model"),
            "device": self.device or "auto-detect",
            "loaded": self._model_loaded,
            "multilingual": not self.model_id.endswith(".en"),
            "parameters": self.AVAILABLE_MODELS.get(self.model_id, "").split(" - ")[0]
        }
    
    @classmethod
    def list_available_models(cls) -> Dict[str, str]:
        """List all available Whisper models."""
        return cls.AVAILABLE_MODELS
    
    def validate_audio_file(self, audio_path: Path) -> bool:
        """Validate audio file for Whisper requirements."""
        if not super().validate_audio_file(audio_path):
            return False
        
        # Check format
        if audio_path.suffix.lower() not in self.get_supported_formats():
            return False
        
        # Whisper can handle large files, but warn for very large ones
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 1000:  # 1GB
            import warnings
            warnings.warn(f"Large file ({file_size_mb:.1f}MB) may take a long time to process")
        
        return True
    
    def estimate_processing_time(self, audio_duration_seconds: float) -> float:
        """
        Estimate processing time based on model size and audio duration.
        
        Returns estimated time in seconds.
        """
        # Rough estimates based on CPU processing (GPU is much faster)
        speed_factors = {
            "tiny": 0.1,
            "tiny.en": 0.1,
            "base": 0.15,
            "base.en": 0.15,
            "small": 0.3,
            "small.en": 0.3,
            "medium": 0.6,
            "medium.en": 0.6,
            "large": 1.2,
            "large-v2": 1.2,
            "large-v3": 1.2,
            "turbo": 0.4
        }
        
        factor = speed_factors.get(self.model_id, 1.0)
        
        # Adjust for GPU
        if self.device == "cuda" or (self.device is None and torch.cuda.is_available()):
            factor *= 0.1  # GPU is roughly 10x faster
        
        return audio_duration_seconds * factor