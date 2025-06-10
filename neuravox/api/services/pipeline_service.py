"""Pipeline integration service for API job processing"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from neuravox.core.pipeline import AudioPipeline
from neuravox.shared.config import UnifiedConfig
from neuravox.shared.file_utils import create_file_id
from neuravox.api.models.database import Job, File, JobFile
from neuravox.api.models.enums import JobStatus, JobType, FileRole
from neuravox.api.services.job_service import JobService
from neuravox.api.services.file_service import FileService
from neuravox.api.utils.exceptions import ProcessingError


class PipelineService:
    """Service for integrating API jobs with audio processing pipeline"""
    
    def __init__(self, config: UnifiedConfig):
        self.config = config
        self.job_service = JobService(config)
        self.file_service = FileService(config)
    
    async def process_job(self, job_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Process a job through the appropriate pipeline"""
        
        try:
            # Get job details
            job = await self.job_service.get_job(job_id, db)
            
            if job.status != JobStatus.PENDING:
                raise ProcessingError(f"Job {job_id} is not in pending status")
            
            # Update job to processing
            await self.job_service.update_job_status(
                job_id, JobStatus.PROCESSING, progress_percent=0, db=db
            )
            
            # Get input files
            files_by_role = await self.job_service.get_job_files(job_id, db)
            input_files = files_by_role.get(FileRole.INPUT, [])
            
            if not input_files:
                raise ProcessingError("No input files found for job")
            
            # Convert file records to paths
            input_paths = [Path(f.file_path) for f in input_files]
            
            # Validate files exist
            for path in input_paths:
                if not path.exists():
                    raise ProcessingError(f"Input file not found: {path}")
            
            # Create progress callback
            progress_callback = self._create_progress_callback(job_id, db)
            
            # Process based on job type
            if job.job_type == JobType.PROCESS:
                result = await self._process_audio_only(
                    job, input_paths, progress_callback, db
                )
            elif job.job_type == JobType.TRANSCRIBE:
                result = await self._transcribe_only(
                    job, input_paths, progress_callback, db
                )
            elif job.job_type == JobType.PIPELINE:
                result = await self._full_pipeline(
                    job, input_paths, progress_callback, db
                )
            else:
                raise ProcessingError(f"Unknown job type: {job.job_type}")
            
            # Mark job as completed
            await self.job_service.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                progress_percent=100,
                result_data=result,
                db=db
            )
            
            return result
        
        except Exception as e:
            # Mark job as failed
            await self.job_service.update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=str(e),
                db=db
            )
            raise ProcessingError(f"Job processing failed: {str(e)}")
    
    async def _process_audio_only(
        self,
        job: Job,
        input_paths: List[Path],
        progress_callback: Callable,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Process audio files (splitting only)"""
        
        from neuravox.processor.audio_splitter import AudioProcessor
        
        # Get configuration
        config = self._get_job_config(job)
        
        # Create processor
        processor = AudioProcessor(
            silence_threshold=config.processing.silence_threshold,
            min_silence_duration=config.processing.min_silence_duration,
            pipeline_mode=True
        )
        
        results = []
        total_files = len(input_paths)
        
        for i, input_path in enumerate(input_paths):
            # Update progress
            base_progress = int((i / total_files) * 90)  # Reserve 10% for finalization
            await progress_callback(base_progress)
            
            # Create output directory
            output_dir = config.processed_path / create_file_id(input_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Process file
            start_time = time.time()
            metadata = processor.process_file(input_path, output_dir)
            processing_time = time.time() - start_time
            
            # Save metadata
            metadata.save(output_dir / "processing_metadata.json")
            
            # Register output files
            for chunk in metadata.chunks:
                await self._register_output_file(
                    job.id, chunk.file_path, db
                )
            
            results.append({
                "file": input_path.name,
                "chunks": len(metadata.chunks),
                "processing_time": processing_time,
                "output_dir": str(output_dir)
            })
        
        await progress_callback(100)
        
        return {
            "job_type": "process",
            "files_processed": len(input_paths),
            "total_chunks": sum(r["chunks"] for r in results),
            "results": results
        }
    
    async def _transcribe_only(
        self,
        job: Job,
        input_paths: List[Path],
        progress_callback: Callable,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Transcribe audio files"""
        
        from neuravox.transcriber.engine import AudioTranscriber
        
        # Get configuration
        config = self._get_job_config(job)
        job_config_override = self._parse_config_override(job.config_override)
        
        # Get model from job config or default
        model = (
            job_config_override.get("transcription", {}).get("model") 
            or config.transcription.default_model
        )
        
        # Create transcriber
        transcriber = AudioTranscriber(config)
        
        # Validate model
        if not transcriber.validate_model(model):
            raise ProcessingError(f"Model '{model}' is not available")
        
        results = []
        total_files = len(input_paths)
        
        for i, input_path in enumerate(input_paths):
            # Update progress
            base_progress = int((i / total_files) * 90)
            await progress_callback(base_progress)
            
            # Create output directory
            output_dir = config.transcribed_path / create_file_id(input_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Transcribe file
            start_time = time.time()
            result = await transcriber.transcribe_file(input_path, model, output_dir)
            transcription_time = time.time() - start_time
            
            # Register output files
            if result.get("output_file"):
                await self._register_output_file(
                    job.id, Path(result["output_file"]), db
                )
            if result.get("metadata_file"):
                await self._register_output_file(
                    job.id, Path(result["metadata_file"]), db
                )
            
            results.append({
                "file": input_path.name,
                "model": model,
                "transcription_time": transcription_time,
                "word_count": result.get("metadata", {}).get("word_count", 0),
                "output_file": str(result.get("output_file", ""))
            })
        
        await progress_callback(100)
        
        return {
            "job_type": "transcribe",
            "model": model,
            "files_transcribed": len(input_paths),
            "total_words": sum(r["word_count"] for r in results),
            "results": results
        }
    
    async def _full_pipeline(
        self,
        job: Job,
        input_paths: List[Path],
        progress_callback: Callable,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Run full audio processing and transcription pipeline"""
        
        # Get configuration
        config = self._get_job_config(job)
        job_config_override = self._parse_config_override(job.config_override)
        
        # Get model from job config or default
        model = (
            job_config_override.get("transcription", {}).get("model") 
            or config.transcription.default_model
        )
        
        # Create pipeline
        pipeline = AudioPipeline(config)
        
        # Create progress wrapper that updates job
        async def pipeline_progress_callback():
            # This will be called by the pipeline for progress updates
            # For now, we'll estimate progress based on completion
            pass
        
        # Process files
        start_time = time.time()
        results = await pipeline.process_batch(input_paths, model)
        total_time = time.time() - start_time
        
        # Register output files for each processed file
        for result in results:
            if result.get("status") == "completed":
                file_id = result.get("file_id")
                if file_id:
                    # Register transcription outputs
                    processed_dir = config.processed_path / file_id
                    transcribed_dir = config.transcribed_path / file_id
                    
                    # Register all output files
                    if processed_dir.exists():
                        for output_file in processed_dir.rglob("*"):
                            if output_file.is_file():
                                await self._register_output_file(job.id, output_file, db)
                    
                    if transcribed_dir.exists():
                        for output_file in transcribed_dir.rglob("*"):
                            if output_file.is_file():
                                await self._register_output_file(job.id, output_file, db)
        
        await progress_callback(100)
        
        # Compile summary
        successful = [r for r in results if r.get("status") == "completed"]
        failed = [r for r in results if r.get("status") == "failed"]
        
        return {
            "job_type": "pipeline",
            "model": model,
            "total_files": len(input_paths),
            "successful": len(successful),
            "failed": len(failed),
            "total_time": total_time,
            "results": results
        }
    
    def _create_progress_callback(self, job_id: str, db: AsyncSession) -> Callable:
        """Create progress callback for job updates"""
        
        async def callback(progress: int):
            try:
                await self.job_service.update_job_status(
                    job_id, JobStatus.PROCESSING, progress_percent=progress, db=db
                )
            except Exception:
                pass  # Don't fail job on progress update errors
        
        return callback
    
    def _get_job_config(self, job: Job) -> UnifiedConfig:
        """Get configuration for job with overrides applied"""
        
        config = UnifiedConfig()
        
        if job.config_override:
            try:
                overrides = json.loads(job.config_override)
                
                # Apply processing overrides
                if "processing" in overrides:
                    for key, value in overrides["processing"].items():
                        if hasattr(config.processing, key):
                            setattr(config.processing, key, value)
                
                # Apply transcription overrides
                if "transcription" in overrides:
                    for key, value in overrides["transcription"].items():
                        if hasattr(config.transcription, key):
                            setattr(config.transcription, key, value)
            
            except Exception:
                pass  # Use default config if override parsing fails
        
        return config
    
    def _parse_config_override(self, config_override: Optional[str]) -> Dict[str, Any]:
        """Parse job config override JSON"""
        
        if not config_override:
            return {}
        
        try:
            return json.loads(config_override)
        except Exception:
            return {}
    
    async def _register_output_file(
        self, 
        job_id: str, 
        file_path: Path, 
        db: AsyncSession
    ) -> Optional[str]:
        """Register an output file in the database"""
        
        try:
            if not file_path.exists():
                return None
            
            # Create file record
            file_id = create_file_id(file_path)
            
            # Check if file already exists
            from sqlalchemy import select
            existing_query = select(File).where(File.file_path == str(file_path))
            result = await db.execute(existing_query)
            existing_file = result.scalar_one_or_none()
            
            if existing_file:
                # Add to job if not already associated
                job_file_query = select(JobFile).where(
                    JobFile.job_id == job_id,
                    JobFile.file_id == existing_file.id,
                    JobFile.file_role == FileRole.OUTPUT
                )
                result = await db.execute(job_file_query)
                if not result.scalar_one_or_none():
                    await self.job_service.add_output_file(job_id, existing_file.id, db)
                return existing_file.id
            
            # Create new file record
            db_file = File(
                id=file_id,
                filename=file_path.name,
                original_filename=file_path.name,
                file_path=str(file_path),
                file_size=file_path.stat().st_size,
                mime_type=None,  # Will be determined if needed
                user_id=None  # System-generated file
            )
            
            db.add(db_file)
            await db.commit()
            await db.refresh(db_file)
            
            # Associate with job
            await self.job_service.add_output_file(job_id, db_file.id, db)
            
            return db_file.id
        
        except Exception:
            return None  # Don't fail job on file registration errors