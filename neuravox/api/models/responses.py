"""Pydantic response models for API endpoints"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from .enums import JobStatus, JobType, FileRole


class FileMetadataResponse(BaseModel):
    """File metadata response"""
    id: str = Field(..., description="File ID")
    filename: str = Field(..., description="Current filename")
    original_filename: str = Field(..., description="Original uploaded filename")
    size: int = Field(..., description="File size in bytes")
    mime_type: Optional[str] = Field(None, description="MIME type")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    download_url: Optional[str] = Field(None, description="Download URL")
    # Audio metadata (populated for audio files)
    audio: Optional[Dict[str, Any]] = Field(None, description="Audio metadata")


class JobFileResponse(BaseModel):
    """Job file relationship response"""
    file: FileMetadataResponse = Field(..., description="File metadata")
    role: FileRole = Field(..., description="File role in job")


class ChunkInfoResponse(BaseModel):
    """Information about an audio chunk"""
    index: int = Field(..., description="Chunk index")
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    duration: float = Field(..., description="Duration in seconds")
    file_path: str = Field(..., description="Path to chunk file")
    transcribed: bool = Field(..., description="Whether chunk has been transcribed")


class ProcessingInsightsResponse(BaseModel):
    """Processing insights and metadata"""
    chunks_created: int = Field(..., description="Number of chunks created")
    silence_detection: Dict[str, Any] = Field(..., description="Silence detection results")
    audio_analysis: Dict[str, Any] = Field(..., description="Audio analysis results")
    processing_time: float = Field(..., description="Processing time in seconds")
    effectiveness: str = Field(..., description="Processing effectiveness rating")


class JobSummaryResponse(BaseModel):
    """Job summary information"""
    chunks_processed: Optional[int] = Field(None, description="Number of chunks processed")
    total_duration: Optional[float] = Field(None, description="Total audio duration in seconds")
    transcription_model: Optional[str] = Field(None, description="Transcription model used")
    word_count: Optional[int] = Field(None, description="Total word count")
    character_count: Optional[int] = Field(None, description="Total character count")


class JobStatusResponse(BaseModel):
    """Job status response with processing insights"""
    id: str = Field(..., description="Job ID")
    status: JobStatus = Field(..., description="Current job status")
    job_type: JobType = Field(..., description="Job type")
    progress: int = Field(..., description="Job progress percentage")
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    input_files: List[FileMetadataResponse] = Field(default_factory=list, description="Input files")
    output_files: List[FileMetadataResponse] = Field(default_factory=list, description="Output files")
    current_stage: Optional[str] = Field(None, description="Current processing stage")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    result_summary: Optional[JobSummaryResponse] = Field(None, description="Job result summary")
    # New fields for processing insights
    processing_insights: Optional[ProcessingInsightsResponse] = Field(None, description="Processing insights")
    chunks: Optional[List[ChunkInfoResponse]] = Field(None, description="Chunk information")


class CreateJobResponse(BaseModel):
    """Response for job creation"""
    id: str = Field(..., description="Created job ID")
    status: JobStatus = Field(..., description="Initial job status")
    message: str = Field(..., description="Success message")


class JobListResponse(BaseModel):
    """Response for job listing"""
    jobs: List[JobStatusResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs")
    limit: int = Field(..., description="Requested limit")
    offset: int = Field(..., description="Requested offset")
    has_more: bool = Field(..., description="Whether there are more jobs")


class UploadResponse(BaseModel):
    """File upload response"""
    id: str = Field(..., description="Uploaded file ID")
    filename: str = Field(..., description="Stored filename")
    size: int = Field(..., description="File size in bytes")
    message: str = Field(..., description="Success message")


class ModelInfoResponse(BaseModel):
    """Model information response"""
    key: str = Field(..., description="Model key")
    name: str = Field(..., description="Model display name")
    provider: str = Field(..., description="Model provider")
    model_id: str = Field(..., description="Provider model ID")
    available: bool = Field(..., description="Whether model is available")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Model parameters")


class ConfigResponse(BaseModel):
    """Configuration response"""
    workspace: str = Field(..., description="Workspace path")
    processing: Dict[str, Any] = Field(..., description="Processing configuration")
    transcription: Dict[str, Any] = Field(..., description="Transcription configuration")
    models: List[ModelInfoResponse] = Field(..., description="Available models")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(..., description="Response timestamp")
    database: str = Field(..., description="Database status")
    workspace: str = Field(..., description="Workspace status")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Dependency status")


class ErrorResponse(BaseModel):
    """Error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class ApiKeyResponse(BaseModel):
    """API key response"""
    id: str = Field(..., description="API key ID")
    name: str = Field(..., description="API key name")
    user_id: str = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last used timestamp")
    is_active: bool = Field(..., description="Whether key is active")
    rate_limit_per_minute: int = Field(..., description="Rate limit per minute")


class CreateApiKeyResponse(BaseModel):
    """Create API key response - flattened structure"""
    key: str = Field(..., description="Generated API key (only shown once)")
    id: str = Field(..., description="API key ID")
    name: str = Field(..., description="API key name")
    user_id: str = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last used timestamp")
    is_active: bool = Field(..., description="Whether key is active")
    rate_limit_per_minute: int = Field(..., description="Rate limit per minute")