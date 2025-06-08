"""
Custom exceptions for the Neuravox platform
"""

class NeuravoxError(Exception):
    """Base exception for all Neuravox errors"""
    pass

class PipelineError(NeuravoxError):
    """Error in pipeline processing"""
    pass

class ProcessingError(NeuravoxError):
    """Error in audio processing"""
    pass

class TranscriptionError(NeuravoxError):
    """Error in transcription"""
    pass

class ConfigurationError(NeuravoxError):
    """Error in configuration"""
    pass

class StateError(NeuravoxError):
    """Error in state management"""
    pass