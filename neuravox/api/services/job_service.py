"""Job management service for API"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from neuravox.api.models.database import Job, File, JobFile
from neuravox.api.models.enums import JobStatus, JobType, FileRole
from neuravox.api.utils.exceptions import NotFoundError, ValidationError, ConflictError
from neuravox.shared.config import UnifiedConfig
from neuravox.shared.logging_config import get_logger


class JobService:
    """Service for managing job operations"""
    
    def __init__(self, config: UnifiedConfig):
        self.config = config
        self._running_jobs: Dict[str, asyncio.Task] = {}
        self.logger = get_logger("neuravox.api.jobs")
    
    async def create_job(
        self,
        job_type: JobType,
        file_ids: List[str],
        config_override: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        db: AsyncSession = None
    ) -> Job:
        """Create a new job"""
        
        # Validate files exist
        file_query = select(File).where(File.id.in_(file_ids))
        result = await db.execute(file_query)
        files = list(result.scalars().all())
        
        if len(files) != len(file_ids):
            found_ids = {f.id for f in files}
            missing_ids = set(file_ids) - found_ids
            raise ValidationError(f"Files not found: {', '.join(missing_ids)}")
        
        # Create job record
        job_id = str(uuid4())
        job = Job(
            id=job_id,
            status=JobStatus.PENDING,
            job_type=job_type,
            user_id=user_id,
            config_override=json.dumps(config_override) if config_override else None
        )
        
        db.add(job)
        
        # Create job-file relationships
        for file in files:
            job_file = JobFile(
                job_id=job_id,
                file_id=file.id,
                file_role=FileRole.INPUT
            )
            db.add(job_file)
        
        await db.commit()
        await db.refresh(job)
        
        return job
    
    async def get_job(self, job_id: str, db: AsyncSession) -> Job:
        """Get job by ID with relationships"""
        query = select(Job).where(Job.id == job_id)
        result = await db.execute(query)
        job = result.scalar_one_or_none()
        
        if not job:
            raise NotFoundError("Job", job_id)
        
        return job
    
    async def list_jobs(
        self,
        user_id: Optional[str] = None,
        status: Optional[JobStatus] = None,
        job_type: Optional[JobType] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True,
        db: AsyncSession = None
    ) -> tuple[List[Job], int]:
        """List jobs with filters and pagination"""
        
        # Build query
        query = select(Job)
        count_query = select(Job.id)
        
        # Apply filters
        filters = []
        if user_id:
            filters.append(Job.user_id == user_id)
        if status:
            filters.append(Job.status == status)
        if job_type:
            filters.append(Job.job_type == job_type)
        
        if filters:
            filter_condition = and_(*filters)
            query = query.where(filter_condition)
            count_query = count_query.where(filter_condition)
        
        # Get total count
        count_result = await db.execute(count_query)
        total = len(list(count_result.scalars().all()))
        
        # Apply ordering
        order_column = getattr(Job, order_by, Job.created_at)
        if order_desc:
            order_column = order_column.desc()
        query = query.order_by(order_column)
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        # Execute query
        result = await db.execute(query)
        jobs = list(result.scalars().all())
        
        return jobs, total
    
    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        progress_percent: Optional[int] = None,
        error_message: Optional[str] = None,
        error_context: Optional[Dict[str, Any]] = None,
        result_data: Optional[Dict[str, Any]] = None,
        db: AsyncSession = None
    ) -> Job:
        """Update job status and related fields with enhanced error context"""
        
        job = await self.get_job(job_id, db)
        
        # Log status change
        old_status = job.status
        self.logger.info(
            "job_status_update",
            job_id=job_id,
            old_status=old_status.value if hasattr(old_status, 'value') else str(old_status),
            new_status=status.value,
            progress=progress_percent
        )
        
        # Update status
        job.status = status
        job.updated_at = datetime.utcnow()
        
        # Update timestamps based on status
        if status == JobStatus.PROCESSING and old_status == JobStatus.PENDING:
            job.started_at = datetime.utcnow()
            self.logger.info("job_started", job_id=job_id)
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            job.completed_at = datetime.utcnow()
            duration = (job.completed_at - job.started_at).total_seconds() if job.started_at else None
            
            if status == JobStatus.COMPLETED:
                self.logger.info(
                    "job_completed",
                    job_id=job_id,
                    duration_seconds=duration
                )
            elif status == JobStatus.FAILED:
                self.logger.warning(
                    "job_failed",
                    job_id=job_id,
                    error_message=error_message,
                    duration_seconds=duration
                )
            else:  # CANCELLED
                self.logger.info(
                    "job_cancelled",
                    job_id=job_id,
                    duration_seconds=duration
                )
        
        # Update optional fields
        if progress_percent is not None:
            job.progress_percent = max(0, min(100, progress_percent))
        
        if error_message is not None:
            job.error_message = error_message
        
        if error_context is not None:
            job.error_context = json.dumps(error_context)
            self.logger.debug(
                "job_error_context_stored",
                job_id=job_id,
                context_keys=list(error_context.keys())
            )
        
        if result_data is not None:
            job.result_data = json.dumps(result_data)
        
        try:
            await db.commit()
            await db.refresh(job)
        except Exception as e:
            self.logger.error(
                "job_status_update_failed",
                job_id=job_id,
                error=str(e),
                exc_info=True
            )
            raise
        
        return job
    
    async def cancel_job(self, job_id: str, db: AsyncSession) -> Job:
        """Cancel a job"""
        
        job = await self.get_job(job_id, db)
        
        if job.status not in [JobStatus.PENDING, JobStatus.PROCESSING]:
            raise ConflictError(f"Cannot cancel job in {job.status} status")
        
        # Cancel running task if exists
        if job_id in self._running_jobs:
            task = self._running_jobs[job_id]
            task.cancel()
            del self._running_jobs[job_id]
        
        return await self.update_job_status(
            job_id, 
            JobStatus.CANCELLED, 
            error_message="Job cancelled by user",
            db=db
        )
    
    async def get_job_files(self, job_id: str, db: AsyncSession) -> Dict[str, List[File]]:
        """Get files associated with a job, grouped by role"""
        
        query = (
            select(File, JobFile.file_role)
            .join(JobFile, File.id == JobFile.file_id)
            .where(JobFile.job_id == job_id)
        )
        
        result = await db.execute(query)
        file_roles = result.all()
        
        files_by_role = {
            FileRole.INPUT: [],
            FileRole.OUTPUT: [],
            FileRole.INTERMEDIATE: []
        }
        
        for file, role in file_roles:
            files_by_role[role].append(file)
        
        return files_by_role
    
    async def add_output_file(
        self,
        job_id: str,
        file_id: str,
        db: AsyncSession
    ) -> JobFile:
        """Add an output file to a job"""
        
        # Verify job exists
        await self.get_job(job_id, db)
        
        # Verify file exists
        file_query = select(File).where(File.id == file_id)
        result = await db.execute(file_query)
        file = result.scalar_one_or_none()
        
        if not file:
            raise NotFoundError("File", file_id)
        
        # Create job-file relationship
        job_file = JobFile(
            job_id=job_id,
            file_id=file_id,
            file_role=FileRole.OUTPUT
        )
        
        db.add(job_file)
        await db.commit()
        await db.refresh(job_file)
        
        return job_file
    
    async def estimate_completion_time(self, job: Job) -> Optional[datetime]:
        """Estimate job completion time based on progress and history"""
        
        if job.status != JobStatus.PROCESSING or not job.started_at:
            return None
        
        if job.progress_percent <= 0:
            return None
        
        # Calculate elapsed time
        elapsed = datetime.utcnow() - job.started_at
        
        # Estimate remaining time based on progress
        if job.progress_percent >= 100:
            return datetime.utcnow()
        
        estimated_total_seconds = (elapsed.total_seconds() * 100) / job.progress_percent
        remaining_seconds = estimated_total_seconds - elapsed.total_seconds()
        
        return datetime.utcnow() + timedelta(seconds=remaining_seconds)
    
    async def cleanup_old_jobs(
        self,
        completed_days: int = 7,
        failed_days: int = 30,
        db: AsyncSession = None
    ) -> int:
        """Clean up old completed and failed jobs"""
        
        cutoff_completed = datetime.utcnow() - timedelta(days=completed_days)
        cutoff_failed = datetime.utcnow() - timedelta(days=failed_days)
        
        # Find jobs to delete
        query = select(Job).where(
            or_(
                and_(Job.status == JobStatus.COMPLETED, Job.completed_at < cutoff_completed),
                and_(Job.status == JobStatus.FAILED, Job.completed_at < cutoff_failed)
            )
        )
        
        result = await db.execute(query)
        jobs_to_delete = list(result.scalars().all())
        
        # Delete jobs (cascade will handle related records)
        for job in jobs_to_delete:
            await db.delete(job)
        
        await db.commit()
        
        return len(jobs_to_delete)
    
    def register_running_job(self, job_id: str, task: asyncio.Task):
        """Register a running job task"""
        self._running_jobs[job_id] = task
    
    def unregister_running_job(self, job_id: str):
        """Unregister a running job task"""
        self._running_jobs.pop(job_id, None)
    
    def get_running_jobs(self) -> Dict[str, asyncio.Task]:
        """Get currently running jobs"""
        return self._running_jobs.copy()