"""Metadata management interfaces"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any


class IMetadataManager(ABC):
    """Interface for metadata management"""
    
    @abstractmethod
    def add_audio_chunk(self, chunk_id: int, start: float, end: float, output_file: Path):
        """
        Add an audio chunk to metadata
        
        Args:
            chunk_id: Unique chunk identifier
            start: Start time in seconds
            end: End time in seconds
            output_file: Path to the output chunk file
        """
        pass
    
    @abstractmethod
    def add_silence_segment(self, start: float, end: float, confidence: float = 1.0):
        """
        Add a detected silence segment
        
        Args:
            start: Start time in seconds
            end: End time in seconds
            confidence: Detection confidence (0.0 to 1.0)
        """
        pass
    
    @abstractmethod
    def generate_metadata(self) -> Dict[str, Any]:
        """
        Generate complete metadata dictionary
        
        Returns:
            Complete metadata as dictionary
        """
        pass
    
    @abstractmethod
    def save_json(self, output_file: Path):
        """
        Save metadata as JSON file
        
        Args:
            output_file: Path for the JSON output file
        """
        pass
    
    @abstractmethod
    def generate_report(self) -> str:
        """
        Generate human-readable processing report
        
        Returns:
            Formatted report string
        """
        pass
    
    @abstractmethod
    def set_processing_params(self, **params):
        """
        Set processing parameters for metadata
        
        Args:
            **params: Processing parameters to store
        """
        pass
    
    @abstractmethod
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics
        
        Returns:
            Dictionary with processing statistics
        """
        pass