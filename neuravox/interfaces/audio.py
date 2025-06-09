"""Audio processing interfaces"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Tuple
import numpy as np


class IAudioProcessor(ABC):
    """Interface for audio processing implementations"""
    
    @abstractmethod
    def process_file(self, input_file: Path, output_dir: Path, 
                     progress_callback: Optional[Callable] = None):
        """
        Process audio file and return metadata
        
        Args:
            input_file: Path to input audio file
            output_dir: Directory for output chunks
            progress_callback: Optional callback for progress updates
            
        Returns:
            ProcessingMetadata object with all chunk information
        """
        pass
    
    @abstractmethod
    def convert_file(self, input_file: Path, output_file: Path, 
                     format: str = 'flac', **kwargs) -> Dict[str, Any]:
        """
        Convert audio file to different format
        
        Args:
            input_file: Path to input audio file
            output_file: Path for output file
            format: Target format (flac, mp3, wav, etc.)
            **kwargs: Additional conversion parameters
            
        Returns:
            Dictionary with conversion metadata
        """
        pass


class IAudioExporter(ABC):
    """Interface for audio export implementations"""
    
    @abstractmethod
    def export_chunk(self, audio_data: np.ndarray, output_file: Path, 
                    format_type: str = 'wav', quality: str = 'high') -> bool:
        """
        Export audio chunk in specified format
        
        Args:
            audio_data: Audio data to export
            output_file: Path for output file
            format_type: Output format
            quality: Quality setting
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def export_full_file_flac(self, input_file: Path, output_file: Path) -> bool:
        """
        Export full audio file as optimized FLAC
        
        Args:
            input_file: Source audio file
            output_file: Output FLAC file path
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def supported_formats(self) -> Dict[str, Dict[str, Any]]:
        """Get supported output formats and their configurations"""
        pass