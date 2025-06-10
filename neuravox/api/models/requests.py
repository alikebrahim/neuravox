"""Pydantic request models for API endpoints"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator

from .enums import JobType


class ProcessingConfigRequest(BaseModel):
    """Audio processing configuration override - mirrors all CLI parameters"""
    silence_threshold: Optional[float] = Field(None, ge=0.001, le=1.0, description="Silence detection threshold (RMS)")
    min_silence_duration: Optional[float] = Field(None, ge=0.1, le=300.0, description="Minimum silence duration in seconds")
    output_format: Optional[str] = Field(None, description="Output format (flac, wav, mp3)")
    sample_rate: Optional[int] = Field(None, description="Target sample rate in Hz")
    normalize: Optional[bool] = Field(None, description="Normalize audio levels")
    compression_level: Optional[int] = Field(None, ge=0, le=12, description="FLAC compression level")
    chunk_boundary: Optional[str] = Field(None, description="Chunk boundary method (simple, overlap)")
    
    @validator('output_format')
    def validate_output_format(cls, v):
        if v and v not in ['flac', 'wav', 'mp3']:
            raise ValueError("Output format must be one of: flac, wav, mp3")
        return v
    
    @validator('sample_rate')
    def validate_sample_rate(cls, v):
        if v and v not in [8000, 16000, 22050, 44100, 48000]:
            raise ValueError("Sample rate must be one of: 8000, 16000, 22050, 44100, 48000")
        return v


class TranscriptionConfigRequest(BaseModel):
    """Transcription configuration override - mirrors all CLI parameters"""
    model: Optional[str] = Field(None, description="Transcription model to use")
    chunk_processing: Optional[bool] = Field(None, description="Process chunks separately")
    combine_chunks: Optional[bool] = Field(None, description="Combine chunk results into single file")
    include_timestamps: Optional[bool] = Field(None, description="Include word-level timestamps in output")
    max_concurrent: Optional[int] = Field(None, ge=1, le=10, description="Maximum concurrent transcriptions")
    language: Optional[str] = Field(None, description="Language code for transcription (e.g., 'en', 'es')")
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0, description="Model temperature for diversity")
    
    @validator('model')
    def validate_model(cls, v):
        valid_models = ['google-gemini', 'openai-whisper', 'whisper-base', 'whisper-turbo']
        if v and v not in valid_models:
            raise ValueError(f"Model must be one of: {', '.join(valid_models)}")
        return v


class JobConfigRequest(BaseModel):
    """Job configuration overrides"""
    processing: Optional[ProcessingConfigRequest] = None
    transcription: Optional[TranscriptionConfigRequest] = None


class CreateJobRequest(BaseModel):
    """Request to create a new job"""
    job_type: JobType = Field(..., description="Type of job to create")
    file_ids: List[str] = Field(..., min_items=1, description="List of file IDs to process")
    config: Optional[JobConfigRequest] = Field(None, description="Configuration overrides")
    
    @validator('file_ids')
    def validate_file_ids(cls, v):
        if not v:
            raise ValueError("At least one file ID is required")
        return v


class ProcessRequest(BaseModel):
    """Request for audio processing only - mirrors CLI 'process' command"""
    file_ids: List[str] = Field(..., min_items=1, description="List of file IDs to process")
    config: Optional[ProcessingConfigRequest] = Field(None, description="Processing configuration overrides")
    # Direct parameter overrides (like CLI flags)
    silence_threshold: Optional[float] = Field(None, description="Override silence threshold")
    min_silence_duration: Optional[float] = Field(None, description="Override minimum silence duration")
    output_format: Optional[str] = Field(None, description="Override output format")


class TranscribeRequest(BaseModel):
    """Request for transcription only - mirrors CLI 'transcribe' command"""
    file_ids: List[str] = Field(..., min_items=1, description="List of file IDs to transcribe")
    model: Optional[str] = Field(None, description="Transcription model to use")
    config: Optional[TranscriptionConfigRequest] = Field(None, description="Transcription configuration overrides")
    # Direct parameter overrides (like CLI flags)
    timestamps: Optional[bool] = Field(None, description="Include timestamps")
    language: Optional[str] = Field(None, description="Language code")
    max_concurrent: Optional[int] = Field(None, description="Max concurrent transcriptions")


class PipelineRequest(BaseModel):
    """Request for full pipeline processing"""
    file_ids: List[str] = Field(..., min_items=1, description="List of file IDs to process")
    config: Optional[JobConfigRequest] = Field(None, description="Configuration overrides")


class JobListRequest(BaseModel):
    """Request parameters for listing jobs"""
    status: Optional[str] = Field(None, description="Filter by job status")
    job_type: Optional[JobType] = Field(None, description="Filter by job type")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    limit: int = Field(50, ge=1, le=200, description="Maximum number of jobs to return")
    offset: int = Field(0, ge=0, description="Number of jobs to skip")
    order_by: str = Field("created_at", description="Field to order by")
    order_desc: bool = Field(True, description="Order in descending order")


class ConvertRequest(BaseModel):
    """Request for audio format conversion"""
    file_ids: List[str] = Field(..., min_items=1, description="List of file IDs to convert")
    output_format: str = Field("flac", description="Target audio format")
    sample_rate: Optional[int] = Field(None, description="Target sample rate in Hz")
    bit_rate: Optional[int] = Field(None, description="Target bit rate (for lossy formats)")
    channels: Optional[int] = Field(None, description="Number of audio channels (1=mono, 2=stereo)")


class CreateApiKeyRequest(BaseModel):
    """Request to create a new API key"""
    name: str = Field(..., min_length=1, max_length=100, description="Name for the API key")
    user_id: str = Field(..., min_length=1, max_length=100, description="User identifier")
    rate_limit_per_minute: int = Field(60, ge=1, le=1000, description="Rate limit per minute")