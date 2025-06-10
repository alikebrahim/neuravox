"""Custom exception classes for the API"""

import traceback
from datetime import datetime
from typing import Any, Dict, Optional


class NeuravoxAPIException(Exception):
    """Base exception for Neuravox API"""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_type: str = "api_error",
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = False,
        operation: str = None,
        preserve_traceback: bool = False
    ):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        self.details = details or {}
        self.retryable = retryable
        self.operation = operation
        self.timestamp = datetime.utcnow()
        
        # Preserve original traceback if requested
        if preserve_traceback:
            self.details["traceback"] = traceback.format_exc()
        
        super().__init__(self.message)
    
    def to_dict(self, include_debug: bool = False) -> Dict[str, Any]:
        """Convert exception to dictionary for API response"""
        result = {
            "type": self.error_type,
            "message": self.message,
            "details": self.details,
            "retryable": self.retryable,
            "timestamp": self.timestamp.isoformat()
        }
        
        if self.operation:
            result["operation"] = self.operation
        
        if include_debug and "traceback" in self.details:
            result["traceback"] = self.details["traceback"]
        
        return result


class ValidationError(NeuravoxAPIException):
    """Validation error"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_type="validation_error",
            details=details
        )


class NotFoundError(NeuravoxAPIException):
    """Resource not found error"""
    
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found: {identifier}",
            status_code=404,
            error_type="not_found",
            details={"resource": resource, "identifier": identifier}
        )


class AuthenticationError(NeuravoxAPIException):
    """Authentication error"""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=401,
            error_type="authentication_error"
        )


class AuthorizationError(NeuravoxAPIException):
    """Authorization error"""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            status_code=403,
            error_type="authorization_error"
        )


class ConflictError(NeuravoxAPIException):
    """Resource conflict error"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=409,
            error_type="conflict_error",
            details=details
        )


class ProcessingError(NeuravoxAPIException):
    """Processing error"""
    
    def __init__(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = False,
        operation: str = None
    ):
        super().__init__(
            message=message,
            status_code=422,
            error_type="processing_error",
            details=details,
            retryable=retryable,
            operation=operation
        )


class RateLimitError(NeuravoxAPIException):
    """Rate limit exceeded error"""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            status_code=429,
            error_type="rate_limit_error"
        )


class ServiceUnavailableError(NeuravoxAPIException):
    """Service unavailable error"""
    
    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(
            message=message,
            status_code=503,
            error_type="service_unavailable",
            retryable=True  # Service unavailable is typically retryable
        )


class ConfigurationError(NeuravoxAPIException):
    """Configuration error"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_type="configuration_error",
            details=details
        )


class ExternalServiceError(NeuravoxAPIException):
    """External service error (AI models, etc.)"""
    
    def __init__(
        self, 
        message: str, 
        service_name: str,
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = True
    ):
        details = details or {}
        details["service"] = service_name
        
        super().__init__(
            message=message,
            status_code=502,
            error_type="external_service_error",
            details=details,
            retryable=retryable
        )