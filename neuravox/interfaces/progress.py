"""Progress tracking interfaces"""

from abc import ABC, abstractmethod
from typing import Optional


class IProgressTracker(ABC):
    """Interface for progress tracking implementations"""
    
    @abstractmethod
    def add_task(self, name: str, description: str, total: int) -> str:
        """
        Add a new task to track
        
        Args:
            name: Unique name for the task
            description: Human-readable description
            total: Total number of items to process
            
        Returns:
            Task identifier
        """
        pass
    
    @abstractmethod
    def update_task(self, name: str, advance: int = 1, description: Optional[str] = None):
        """
        Update task progress
        
        Args:
            name: Task name
            advance: Number of items completed
            description: Optional updated description
        """
        pass
    
    @abstractmethod
    def finish_task(self, name: str):
        """
        Mark task as complete
        
        Args:
            name: Task name to complete
        """
        pass
    
    @abstractmethod
    def get_elapsed_time(self) -> float:
        """
        Get total elapsed time since tracker creation
        
        Returns:
            Elapsed time in seconds
        """
        pass
    
    @abstractmethod
    def __enter__(self):
        """Context manager entry"""
        pass
    
    @abstractmethod
    def __exit__(self, *args):
        """Context manager exit"""
        pass