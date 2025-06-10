"""Audio processing and transcription endpoints"""

import asyncio
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from neuravox.db.database import get_db_session
from neuravox.shared.config import UnifiedConfig
from neuravox.shared.logging_config import get_logger, LoggingContextManager
from neuravox.api.services.job_service import JobService
from neuravox.api.services.pipeline_service import PipelineService
from neuravox.api.models.requests import (
    ProcessRequest, TranscribeRequest, PipelineRequest, ConvertRequest
)
from neuravox.api.models.responses import CreateJobResponse
from neuravox.api.models.enums import JobType
from neuravox.api.utils.exceptions import ValidationError, ProcessingError
from neuravox.api.middleware.auth import get_current_user_id


router = APIRouter()


def get_job_service() -> JobService:
    """Dependency for job service"""
    project_config_path = Path(__file__).parent.parent.parent.parent / "config.yaml"
    config = UnifiedConfig(project_config_path if project_config_path.exists() else None)
    return JobService(config)


def get_pipeline_service() -> PipelineService:
    """Dependency for pipeline service"""
    project_config_path = Path(__file__).parent.parent.parent.parent / "config.yaml"
    config = UnifiedConfig(project_config_path if project_config_path.exists() else None)
    return PipelineService(config)


async def process_job_background(job_id: str, pipeline_service: PipelineService):
    """Background task for processing jobs with comprehensive error handling"""
    logger = get_logger("neuravox.api.background")
    operation_id = str(uuid.uuid4())
    
    # Set up logging context for background processing
    with LoggingContextManager(job_id=job_id, operation_id=operation_id):
        logger.info(
            "background_job_started",
            job_id=job_id,
            operation_id=operation_id
        )
        
        from neuravox.db.database import get_database_manager
        
        db_manager = get_database_manager()
        
        try:
            async for db in db_manager.get_session():
                try:
                    await pipeline_service.process_job(job_id, db)
                    
                    logger.info(
                        "background_job_completed",
                        job_id=job_id,
                        operation_id=operation_id
                    )
                    
                except (ValidationError, ProcessingError) as e:
                    # Expected errors - already logged by pipeline service
                    logger.warning(
                        "background_job_failed_expected",
                        job_id=job_id,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        operation_id=operation_id
                    )
                    
                except Exception as e:
                    # Unexpected errors in background processing
                    logger.error(
                        "background_job_failed_unexpected",
                        job_id=job_id,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        operation_id=operation_id,
                        exc_info=True
                    )
                    
                    # Try to update job status if possible
                    try:
                        from neuravox.api.models.enums import JobStatus
                        job_service = JobService(pipeline_service.config)
                        await job_service.update_job_status(
                            job_id,
                            JobStatus.FAILED,
                            error_message=f"Background processing failed: {str(e)}",
                            error_context={"background_error": True, "operation_id": operation_id},
                            db=db
                        )
                    except Exception as update_error:
                        logger.error(
                            "failed_to_update_background_job_status",
                            job_id=job_id,
                            update_error=str(update_error),
                            original_error=str(e)
                        )
                
                break  # Exit the async generator loop
                
        except Exception as e:
            # Database connection or other infrastructure errors
            logger.critical(
                "background_job_infrastructure_failure",
                job_id=job_id,
                error_type=type(e).__name__,
                error_message=str(e),
                operation_id=operation_id,
                exc_info=True
            )


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