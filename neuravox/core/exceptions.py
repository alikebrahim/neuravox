"""
Custom exceptions for the Neuravox platform
"""

class NeuravoxError(Exception):
    """Base exception for all Neuravox errors"""
    pass

class PipelineError(NeuravoxError):
    """Error in pipeline processing"""
    pass

