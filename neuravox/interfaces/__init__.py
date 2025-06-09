"""
Interface definitions for the Neuravox audio processing framework.

This module provides abstract base classes that define contracts for
core functionality, enabling better testability and modularity.
"""

from .audio import IAudioProcessor, IAudioExporter
from .transcription import AudioTranscriptionModel
from .state import IStateManager
from .progress import IProgressTracker
from .metadata import IMetadataManager
from .config import IConfigManager

__all__ = [
    'IAudioProcessor',
    'IAudioExporter', 
    'AudioTranscriptionModel',
    'IStateManager',
    'IProgressTracker',
    'IMetadataManager',
    'IConfigManager'
]