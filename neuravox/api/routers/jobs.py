"""Job management endpoints"""

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from neuravox.db.database import get_db_session
from neuravox.shared.config import UnifiedConfig
from neuravox.api.services.job_service import JobService
from neuravox.api.services.pipeline_service import PipelineService
from neuravox.api.models.requests import CreateJobRequest, JobListRequest
from neuravox.api.models.responses import (
    CreateJobResponse, JobStatusResponse, JobListResponse, 
    FileMetadataResponse, JobSummaryResponse, ProcessingInsightsResponse,
    ChunkInfoResponse
)
from neuravox.api.models.enums import JobStatus, JobType
from neuravox.api.utils.exceptions import NotFoundError, ValidationError, ConflictError
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


@router.post("/jobs", response_model=CreateJobResponse, status_code=201)
async def create_job(
    request: CreateJobRequest,
    user_id: Optional[str] = Depends(get_current_user_id),
    job_service: JobService = Depends(get_job_service),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new processing job"""
    
    try:
        # Convert config to dict if provided
        config_override = None
        if request.config:
            config_override = request.config.dict(exclude_none=True)
        
        job = await job_service.create_job(
            job_type=request.job_type,
            file_ids=request.file_ids,
            config_override=config_override,
            user_id=user_id,
            db=db
        )
        
        return CreateJobResponse(
            id=job.id,
            status=job.status,
            message="Job created successfully"
        )
    
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    user_id: Optional[str] = Query(None),
    status: Optional[JobStatus] = Query(None),
    job_type: Optional[JobType] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    order_by: str = Query("created_at"),
    order_desc: bool = Query(True),
    job_service: JobService = Depends(get_job_service),
    db: AsyncSession = Depends(get_db_session)
):
    """List jobs with filtering and pagination"""
    
    try:
        jobs, total = await job_service.list_jobs(
            user_id=user_id,
            status=status,
            job_type=job_type,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_desc=order_desc,
            db=db
        )
        
        # Convert to response models
        job_responses = []
        for job in jobs:
            # Get job files
            files_by_role = await job_service.get_job_files(job.id, db)
            
            # Convert files to response models
            input_files = [
                FileMetadataResponse(
                    id=f.id,
                    filename=f.filename,
                    original_filename=f.original_filename,
                    size=f.file_size,
                    mime_type=f.mime_type,
                    uploaded_at=f.uploaded_at,
                    download_url=f"/api/v1/files/{f.id}/download",
                    audio=None
                )
                for f in files_by_role.get("input", [])
            ]
            
            output_files = [
                FileMetadataResponse(
                    id=f.id,
                    filename=f.filename,
                    original_filename=f.original_filename,
                    size=f.file_size,
                    mime_type=f.mime_type,
                    uploaded_at=f.uploaded_at,
                    download_url=f"/api/v1/files/{f.id}/download",
                    audio=None
                )
                for f in files_by_role.get("output", [])
            ]
            
            # Parse result data for summary and insights
            result_summary = None
            processing_insights = None
            chunks_info = None
            
            if job.result_data:
                try:
                    import json
                    result_dict = json.loads(job.result_data)
                    
                    # Extract summary data
                    summary_data = {
                        "chunks_processed": result_dict.get("total_chunks"),
                        "total_duration": result_dict.get("total_duration"),
                        "transcription_model": result_dict.get("model"),
                        "word_count": result_dict.get("total_words"),
                        "character_count": result_dict.get("total_characters")
                    }
                    result_summary = JobSummaryResponse(**{k: v for k, v in summary_data.items() if v is not None})
                    
                    # Extract processing insights for PROCESS and PIPELINE jobs
                    if job.job_type in [JobType.PROCESS, JobType.PIPELINE]:
                        results = result_dict.get("results", [])
                        if results:
                            # Aggregate processing insights from results
                            total_chunks = sum(r.get("chunks", 0) for r in results)
                            total_processing_time = sum(r.get("processing_time", 0) for r in results)
                            
                            # Check for metadata files to get detailed insights
                            if job.job_type == JobType.PROCESS and results[0].get("output_dir"):
                                # Try to load processing metadata
                                try:
                                    from pathlib import Path
                                    metadata_path = Path(results[0]["output_dir"]) / "processing_metadata.json"
                                    if metadata_path.exists():
                                        with open(metadata_path) as f:
                                            metadata = json.load(f)
                                            
                                        # Extract processing insights
                                        processing_params = metadata.get("processing_params", {})
                                        processing_insights = ProcessingInsightsResponse(
                                            chunks_created=total_chunks,
                                            silence_detection={
                                                "threshold_used": processing_params.get("silence_threshold", 0.01),
                                                "min_duration_used": processing_params.get("min_silence_duration", 25.0),
                                                "gaps_found": total_chunks - 1 if total_chunks > 0 else 0,
                                                "total_silence_removed": 0  # Calculate from metadata if available
                                            },
                                            audio_analysis={
                                                "original_duration": metadata.get("audio_info", {}).get("duration", 0),
                                                "processed_duration": sum(c["duration"] for c in metadata.get("chunks", [])),
                                                "format_conversion": f"{metadata.get('audio_info', {}).get('format', 'unknown')} -> flac",
                                                "sample_rate_conversion": f"{metadata.get('audio_info', {}).get('sample_rate', 'unknown')} -> 16000"
                                            },
                                            processing_time=total_processing_time,
                                            effectiveness="good" if total_chunks > 1 else "no_splitting"
                                        )
                                        
                                        # Extract chunk information
                                        chunks_info = [
                                            ChunkInfoResponse(
                                                index=chunk["chunk_index"],
                                                start_time=chunk["start_time"],
                                                end_time=chunk["end_time"],
                                                duration=chunk["duration"],
                                                file_path=chunk["file_path"],
                                                transcribed=job.job_type == JobType.PIPELINE
                                            )
                                            for chunk in metadata.get("chunks", [])
                                        ]
                                except Exception:
                                    pass  # Metadata not available
                except Exception:
                    pass
            
            # Estimate completion time
            estimated_completion = await job_service.estimate_completion_time(job)
            
            job_response = JobStatusResponse(
                id=job.id,
                status=job.status,
                job_type=job.job_type,
                progress=job.progress_percent,
                created_at=job.created_at,
                updated_at=job.updated_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                estimated_completion=estimated_completion,
                input_files=input_files,
                output_files=output_files,
                current_stage=None,  # TODO: Implement stage tracking
                error_message=job.error_message,
                result_summary=result_summary,
                processing_insights=processing_insights,
                chunks=chunks_info
            )
            
            job_responses.append(job_response)
        
        return JobListResponse(
            jobs=job_responses,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + limit < total
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
    db: AsyncSession = Depends(get_db_session)
):
    """Get detailed job status and results"""
    
    try:
        job = await job_service.get_job(job_id, db)
        
        # Get job files
        files_by_role = await job_service.get_job_files(job.id, db)
        
        # Convert files to response models
        input_files = [
            FileMetadataResponse(
                id=f.id,
                filename=f.filename,
                original_filename=f.original_filename,
                file_size=f.file_size,
                mime_type=f.mime_type,
                uploaded_at=f.uploaded_at,
                download_url=f"/api/v1/files/{f.id}/download"
            )
            for f in files_by_role.get("input", [])
        ]
        
        output_files = [
            FileMetadataResponse(
                id=f.id,
                filename=f.filename,
                original_filename=f.original_filename,
                file_size=f.file_size,
                mime_type=f.mime_type,
                uploaded_at=f.uploaded_at,
                download_url=f"/api/v1/files/{f.id}/download"
            )
            for f in files_by_role.get("output", [])
        ]
        
        # Parse result data for summary and insights
        result_summary = None
        processing_insights = None
        chunks_info = None
        
        if job.result_data:
            try:
                import json
                result_dict = json.loads(job.result_data)
                
                # Extract summary data
                summary_data = {
                    "chunks_processed": result_dict.get("total_chunks"),
                    "total_duration": result_dict.get("total_duration"),
                    "transcription_model": result_dict.get("model"),
                    "word_count": result_dict.get("total_words"),
                    "character_count": result_dict.get("total_characters")
                }
                result_summary = JobSummaryResponse(**{k: v for k, v in summary_data.items() if v is not None})
                
                # Extract processing insights for PROCESS and PIPELINE jobs
                if job.job_type in [JobType.PROCESS, JobType.PIPELINE]:
                    results = result_dict.get("results", [])
                    if results:
                        # Aggregate processing insights from results
                        total_chunks = sum(r.get("chunks", 0) for r in results)
                        total_processing_time = sum(r.get("processing_time", 0) for r in results)
                        
                        # Check for metadata files to get detailed insights
                        if results[0].get("output_dir"):
                            # Try to load processing metadata
                            try:
                                from pathlib import Path
                                metadata_path = Path(results[0]["output_dir"]) / "processing_metadata.json"
                                if metadata_path.exists():
                                    with open(metadata_path) as f:
                                        metadata = json.load(f)
                                        
                                    # Extract processing insights
                                    processing_params = metadata.get("processing_params", {})
                                    processing_insights = ProcessingInsightsResponse(
                                        chunks_created=total_chunks,
                                        silence_detection={
                                            "threshold_used": processing_params.get("silence_threshold", 0.01),
                                            "min_duration_used": processing_params.get("min_silence_duration", 25.0),
                                            "gaps_found": total_chunks - 1 if total_chunks > 0 else 0,
                                            "total_silence_removed": 0  # Calculate from metadata if available
                                        },
                                        audio_analysis={
                                            "original_duration": metadata.get("audio_info", {}).get("duration", 0),
                                            "processed_duration": sum(c["duration"] for c in metadata.get("chunks", [])),
                                            "format_conversion": f"{metadata.get('audio_info', {}).get('format', 'unknown')} -> flac",
                                            "sample_rate_conversion": f"{metadata.get('audio_info', {}).get('sample_rate', 'unknown')} -> 16000"
                                        },
                                        processing_time=total_processing_time,
                                        effectiveness="good" if total_chunks > 1 else "no_splitting"
                                    )
                                    
                                    # Extract chunk information
                                    chunks_info = [
                                        ChunkInfoResponse(
                                            index=chunk["chunk_index"],
                                            start_time=chunk["start_time"],
                                            end_time=chunk["end_time"],
                                            duration=chunk["duration"],
                                            file_path=chunk["file_path"],
                                            transcribed=job.job_type == JobType.PIPELINE
                                        )
                                        for chunk in metadata.get("chunks", [])
                                    ]
                            except Exception:
                                pass  # Metadata not available
            except Exception:
                pass
        
        # Estimate completion time
        estimated_completion = await job_service.estimate_completion_time(job)
        
        return JobStatusResponse(
            id=job.id,
            status=job.status,
            job_type=job.job_type,
            progress=job.progress_percent,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            estimated_completion=estimated_completion,
            input_files=input_files,
            output_files=output_files,
            current_stage=None,  # TODO: Implement stage tracking
            error_message=job.error_message,
            result_summary=result_summary,
            processing_insights=processing_insights,
            chunks=chunks_info
        )
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job: {str(e)}")


@router.delete("/jobs/{job_id}", status_code=204)
async def cancel_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
    db: AsyncSession = Depends(get_db_session)
):
    """Cancel a job"""
    
    try:
        await job_service.cancel_job(job_id, db)
        return
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")


@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
    db: AsyncSession = Depends(get_db_session)
):
    """Retry a failed job"""
    
    try:
        job = await job_service.get_job(job_id, db)
        
        if job.status != JobStatus.FAILED:
            raise ConflictError(f"Cannot retry job in {job.status} status")
        
        # Reset job to pending status
        job = await job_service.update_job_status(
            job_id,
            JobStatus.PENDING,
            progress_percent=0,
            error_message=None,
            db=db
        )
        
        return {
            "message": "Job queued for retry",
            "job_id": job.id,
            "status": job.status
        }
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retry job: {str(e)}")


@router.post("/jobs/{job_id}/resume")
async def resume_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Resume an interrupted job (mirrors CLI 'resume' command)"""
    
    try:
        from fastapi import BackgroundTasks as BT
        if background_tasks is None:
            background_tasks = BT()
            
        job = await job_service.get_job(job_id, db)
        
        # Check if job can be resumed
        if job.status not in [JobStatus.FAILED, JobStatus.CANCELLED]:
            raise ConflictError(f"Cannot resume job in {job.status} status")
        
        # Reset job to processing status
        job = await job_service.update_job_status(
            job_id,
            JobStatus.PROCESSING,
            progress_percent=job.progress_percent or 0,  # Keep existing progress
            error_message=None,
            db=db
        )
        
        # Import background task handler
        from neuravox.api.routers.processing import process_job_background
        
        # Resume processing in background
        background_tasks.add_task(process_job_background, job.id, pipeline_service)
        
        return {
            "message": "Job resumed successfully",
            "job_id": job.id,
            "status": job.status,
            "progress": job.progress_percent
        }
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resume job: {str(e)}")


@router.get("/jobs/{job_id}/preview")
async def get_job_preview(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
    db: AsyncSession = Depends(get_db_session)
):
    """Get processing preview for a job (available after processing, before transcription)"""
    
    try:
        job = await job_service.get_job(job_id, db)
        
        # Check if job has processing data
        if job.job_type not in [JobType.PROCESS, JobType.PIPELINE]:
            raise HTTPException(
                status_code=400, 
                detail="Preview only available for PROCESS or PIPELINE jobs"
            )
        
        if job.status == JobStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail="Job has not started processing yet"
            )
        
        # Parse result data for processing insights
        if not job.result_data:
            raise HTTPException(
                status_code=404,
                detail="No processing data available yet"
            )
        
        try:
            import json
            result_dict = json.loads(job.result_data)
            results = result_dict.get("results", [])
            
            if not results:
                raise HTTPException(
                    status_code=404,
                    detail="No processing results available"
                )
            
            # Aggregate data from all processed files
            total_files = len(results)
            total_chunks = sum(r.get("chunks", 0) for r in results)
            total_processing_time = sum(r.get("processing_time", 0) for r in results)
            
            # Calculate chunk distribution
            chunk_durations = []
            total_duration = 0
            silence_removed = 0
            
            # Try to load detailed metadata
            for result in results:
                if result.get("output_dir"):
                    try:
                        from pathlib import Path
                        metadata_path = Path(result["output_dir"]) / "processing_metadata.json"
                        if metadata_path.exists():
                            with open(metadata_path) as f:
                                metadata = json.load(f)
                                
                            # Extract chunk durations
                            for chunk in metadata.get("chunks", []):
                                chunk_durations.append(chunk["duration"])
                            
                            # Calculate total duration and silence
                            audio_info = metadata.get("audio_info", {})
                            original_duration = audio_info.get("duration", 0)
                            total_duration += original_duration
                            
                            # Calculate silence removed
                            chunks_duration = sum(c["duration"] for c in metadata.get("chunks", []))
                            if original_duration > 0:
                                silence_removed += (original_duration - chunks_duration)
                    except Exception:
                        pass
            
            # Calculate effectiveness metrics
            effectiveness = "unknown"
            recommendations = []
            
            if chunk_durations:
                min_duration = min(chunk_durations)
                max_duration = max(chunk_durations)
                avg_duration = sum(chunk_durations) / len(chunk_durations)
                
                # Determine effectiveness
                if total_chunks == 0:
                    effectiveness = "no_splitting"
                    recommendations.append("No audio chunks were created - file may be too short or have no silence")
                elif avg_duration < 10:
                    effectiveness = "too_aggressive"
                    recommendations.append("Chunks are very short - consider increasing silence threshold")
                elif avg_duration > 60:
                    effectiveness = "too_conservative"
                    recommendations.append("Chunks are very long - consider decreasing silence threshold")
                elif max_duration > 2 * min_duration:
                    effectiveness = "uneven"
                    recommendations.append("Chunk sizes vary significantly - consider adjusting parameters")
                else:
                    effectiveness = "good"
                    recommendations.append("Good chunk distribution for transcription")
                
                # Additional recommendations
                chunks_under_10s = sum(1 for d in chunk_durations if d < 10)
                chunks_over_60s = sum(1 for d in chunk_durations if d > 60)
                
                if chunks_under_10s > len(chunk_durations) * 0.3:
                    recommendations.append(f"{chunks_under_10s} chunks are under 10s - may be too short for context")
                if chunks_over_60s > len(chunk_durations) * 0.3:
                    recommendations.append(f"{chunks_over_60s} chunks are over 60s - may be too long for accurate transcription")
            
            return {
                "job_id": job_id,
                "processed_at": job.updated_at.isoformat() if job.updated_at else None,
                "ready_for_transcription": job.status == JobStatus.COMPLETED and job.job_type == JobType.PROCESS,
                
                "processing_summary": {
                    "original_files": total_files,
                    "chunks_created": total_chunks,
                    "total_duration": total_duration,
                    "silence_removed": silence_removed,
                    "effectiveness": effectiveness
                },
                
                "chunk_distribution": {
                    "min_chunk_duration": min(chunk_durations) if chunk_durations else 0,
                    "max_chunk_duration": max(chunk_durations) if chunk_durations else 0,
                    "avg_chunk_duration": sum(chunk_durations) / len(chunk_durations) if chunk_durations else 0,
                    "chunks_under_10s": sum(1 for d in chunk_durations if d < 10),
                    "chunks_over_60s": sum(1 for d in chunk_durations if d > 60)
                },
                
                "recommendations": recommendations
            }
        
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=500,
                detail="Failed to parse job results"
            )
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job preview: {str(e)}")