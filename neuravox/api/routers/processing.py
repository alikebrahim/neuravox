"""Audio processing and transcription endpoints"""

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from neuravox.db.database import get_db_session
from neuravox.shared.config import UnifiedConfig
from neuravox.api.services.job_service import JobService
from neuravox.api.services.pipeline_service import PipelineService
from neuravox.api.models.requests import (
    ProcessRequest, TranscribeRequest, PipelineRequest, ConvertRequest
)
from neuravox.api.models.responses import CreateJobResponse
from neuravox.api.models.enums import JobType
from neuravox.api.utils.exceptions import ValidationError
from neuravox.api.middleware.auth import get_current_user_id


router = APIRouter()


def get_job_service() -> JobService:
    """Dependency for job service"""
    config = UnifiedConfig()
    return JobService(config)


def get_pipeline_service() -> PipelineService:
    """Dependency for pipeline service"""
    config = UnifiedConfig()
    return PipelineService(config)


async def process_job_background(job_id: str, pipeline_service: PipelineService):
    """Background task for processing jobs"""
    from neuravox.db.database import get_database_manager
    
    db_manager = get_database_manager()
    async for db in db_manager.get_session():
        try:
            await pipeline_service.process_job(job_id, db)
        except Exception as e:
            print(f"Background job {job_id} failed: {e}")
        break


@router.post("/process", response_model=CreateJobResponse, status_code=202)
async def process_audio(
    request: ProcessRequest,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = Depends(get_current_user_id),
    job_service: JobService = Depends(get_job_service),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    db: AsyncSession = Depends(get_db_session)
):
    """Process audio files (splitting only)"""
    
    try:
        # Convert config to dict if provided
        config_override = {}
        if request.config:
            config_override["processing"] = request.config.dict(exclude_none=True)
        
        # Apply direct parameter overrides (CLI-style)
        if request.silence_threshold is not None or request.min_silence_duration is not None or request.output_format is not None:
            if "processing" not in config_override:
                config_override["processing"] = {}
            if request.silence_threshold is not None:
                config_override["processing"]["silence_threshold"] = request.silence_threshold
            if request.min_silence_duration is not None:
                config_override["processing"]["min_silence_duration"] = request.min_silence_duration
            if request.output_format is not None:
                config_override["processing"]["output_format"] = request.output_format
        
        # Create job
        job = await job_service.create_job(
            job_type=JobType.PROCESS,
            file_ids=request.file_ids,
            config_override=config_override if config_override else None,
            user_id=user_id,
            db=db
        )
        
        # Start background processing
        background_tasks.add_task(process_job_background, job.id, pipeline_service)
        
        return CreateJobResponse(
            id=job.id,
            status=job.status,
            message="Audio processing job started"
        )
    
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start processing: {str(e)}")


@router.post("/transcribe", response_model=CreateJobResponse, status_code=202)
async def transcribe_audio(
    request: TranscribeRequest,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = Depends(get_current_user_id),
    job_service: JobService = Depends(get_job_service),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    db: AsyncSession = Depends(get_db_session)
):
    """Transcribe audio files"""
    
    try:
        # Convert config to dict if provided
        config_override = {}
        if request.config:
            config_override["transcription"] = request.config.dict(exclude_none=True)
        
        # Apply direct parameter overrides (CLI-style)
        direct_params = [
            ("model", request.model),
            ("include_timestamps", request.timestamps),
            ("language", request.language),
            ("max_concurrent", request.max_concurrent)
        ]
        
        for param_name, param_value in direct_params:
            if param_value is not None:
                if "transcription" not in config_override:
                    config_override["transcription"] = {}
                config_override["transcription"][param_name] = param_value
        
        # Create job
        job = await job_service.create_job(
            job_type=JobType.TRANSCRIBE,
            file_ids=request.file_ids,
            config_override=config_override if config_override else None,
            user_id=user_id,
            db=db
        )
        
        # Start background processing
        background_tasks.add_task(process_job_background, job.id, pipeline_service)
        
        return CreateJobResponse(
            id=job.id,
            status=job.status,
            message="Transcription job started"
        )
    
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start transcription: {str(e)}")


@router.post("/pipeline", response_model=CreateJobResponse, status_code=202)
async def full_pipeline(
    request: PipelineRequest,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = Depends(get_current_user_id),
    job_service: JobService = Depends(get_job_service),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    db: AsyncSession = Depends(get_db_session)
):
    """Run full audio processing and transcription pipeline"""
    
    try:
        # Convert config to dict if provided
        config_override = None
        if request.config:
            config_override = request.config.dict(exclude_none=True)
        
        # Create job
        job = await job_service.create_job(
            job_type=JobType.PIPELINE,
            file_ids=request.file_ids,
            config_override=config_override,
            user_id=user_id,
            db=db
        )
        
        # Start background processing
        background_tasks.add_task(process_job_background, job.id, pipeline_service)
        
        return CreateJobResponse(
            id=job.id,
            status=job.status,
            message="Full pipeline job started"
        )
    
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start pipeline: {str(e)}")


@router.post("/convert", response_model=CreateJobResponse, status_code=202)
async def convert_audio(
    request: ConvertRequest,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = Depends(get_current_user_id),
    job_service: JobService = Depends(get_job_service),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    db: AsyncSession = Depends(get_db_session)
):
    """Convert audio files to different formats (mirrors CLI 'convert' command)"""
    
    try:
        # Create config for conversion
        config_override = {
            "processing": {
                "output_format": request.output_format
            }
        }
        
        if request.sample_rate:
            config_override["processing"]["sample_rate"] = request.sample_rate
        
        # Create a CONVERT job type (we'll need to add this to enums)
        # For now, use PROCESS type with conversion config
        job = await job_service.create_job(
            job_type=JobType.PROCESS,  # TODO: Add CONVERT job type
            file_ids=request.file_ids,
            config_override=config_override,
            user_id=user_id,
            db=db
        )
        
        # Start background processing
        background_tasks.add_task(process_job_background, job.id, pipeline_service)
        
        return CreateJobResponse(
            id=job.id,
            status=job.status,
            message="Audio conversion job started"
        )
    
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start conversion: {str(e)}")