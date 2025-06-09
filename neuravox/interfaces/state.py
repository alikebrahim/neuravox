"""State management interfaces"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class IStateManager(ABC):
    """Interface for pipeline state management"""
    
    @abstractmethod
    def start_processing(self, file_id: str, original_path: str):
        """
        Mark file as started processing
        
        Args:
            file_id: Unique identifier for the file
            original_path: Path to the original file
        """
        pass
    
    @abstractmethod
    def update_stage(self, file_id: str, stage: str, metadata: Optional[Dict] = None):
        """
        Update processing stage
        
        Args:
            file_id: Unique identifier for the file
            stage: Current processing stage
            metadata: Optional stage-specific metadata
        """
        pass
    
    @abstractmethod
    def complete_processing(self, file_id: str):
        """
        Mark file as completed
        
        Args:
            file_id: Unique identifier for the file
        """
        pass
    
    @abstractmethod
    def mark_failed(self, file_id: str, error_message: str):
        """
        Mark file as failed
        
        Args:
            file_id: Unique identifier for the file
            error_message: Error description
        """
        pass
    
    @abstractmethod
    def get_file_status(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a file
        
        Args:
            file_id: Unique identifier for the file
            
        Returns:
            Status dictionary or None if not found
        """
        pass
    
    @abstractmethod
    def get_pipeline_summary(self) -> Dict[str, Any]:
        """
        Get overall pipeline summary
        
        Returns:
            Summary of pipeline state including counts and statistics
        """
        pass
    
    @abstractmethod
    def list_files_by_stage(self, stage: str) -> List[str]:
        """
        List all files in a specific stage
        
        Args:
            stage: Processing stage to filter by
            
        Returns:
            List of file IDs in the specified stage
        """
        pass
    
    @abstractmethod
    def clear_failed_files(self) -> int:
        """
        Clear all files marked as failed
        
        Returns:
            Number of files cleared
        """
        pass