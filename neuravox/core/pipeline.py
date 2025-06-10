"""
Main pipeline orchestrator for audio processing and transcription
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncio
import time
import shutil
from datetime import datetime

from neuravox.processor.audio_splitter import AudioProcessor
from neuravox.transcriber.engine import AudioTranscriber
from neuravox.shared.config import UnifiedConfig
from neuravox.shared.progress import UnifiedProgressTracker
from neuravox.shared.metadata import ProcessingMetadata, MetadataManager
from neuravox.shared.file_utils import ensure_directory, create_file_id
from neuravox.shared.logging_config import get_pipeline_logger
from .state_manager import StateManager
from .exceptions import PipelineError
from rich.console import Console


class AudioPipeline:
    """Main pipeline orchestrator"""

    def __init__(self, config: Optional[UnifiedConfig] = None):
        self.config = config or UnifiedConfig()
        self.console = Console()
        self.logger = get_pipeline_logger()
        self.state_manager = StateManager(self.config.workspace)
        
        self.logger.info("Pipeline initialized", workspace=str(self.config.workspace))

        # Initialize modules with pipeline mode
        self.audio_processor = AudioProcessor(
            silence_threshold=self.config.processing.silence_threshold,
            min_silence_duration=self.config.processing.min_silence_duration,
            pipeline_mode=True,
        )
        
        # Validation that configuration was applied correctly
        if self.audio_processor.min_silence_duration != self.config.processing.min_silence_duration:
            error_msg = (
                f"Configuration mismatch: AudioProcessor has min_silence_duration="
                f"{self.audio_processor.min_silence_duration}s but config specifies "
                f"{self.config.processing.min_silence_duration}s"
            )
            self.logger.error(error_msg)
            raise PipelineError(error_msg)
        
        self.transcriber = AudioTranscriber(self.config)

    async def process_file(self, audio_file: Path, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Process single audio file through full pipeline

        Args:
            audio_file: Path to audio file
            model: Transcription model (uses default if None)

        Returns:
            Complete processing results
        """
        self.logger.info(f"Starting pipeline processing", file=str(audio_file))
        
        # Validate input file
        if not audio_file.exists():
            error_msg = f"Audio file not found: {audio_file}"
            self.logger.error(error_msg)
            raise PipelineError(error_msg)

        if not audio_file.is_file():
            error_msg = f"Path is not a file: {audio_file}"
            self.logger.error(error_msg)
            raise PipelineError(error_msg)

        # Check if it's an audio file
        audio_extensions = {
            ".mp3",
            ".wav",
            ".flac",
            ".m4a",
            ".ogg",
            ".opus",
            ".wma",
            ".aac",
            ".mp4",
        }
        if audio_file.suffix.lower() not in audio_extensions:
            error_msg = f"Unsupported file format: {audio_file.suffix}"
            self.logger.error(error_msg, supported_formats=list(audio_extensions))
            raise PipelineError(error_msg)

        # Check file size (warn if very large)
        file_size_mb = audio_file.stat().st_size / (1024 * 1024)
        self.logger.info(f"File size: {file_size_mb:.1f}MB", file_size_mb=file_size_mb)
        if file_size_mb > 1000:  # 1GB
            self.logger.warning(f"Large file ({file_size_mb:.1f}MB) may take a long time to process")
            self.console.print(
                f"[yellow]Warning: Large file ({file_size_mb:.1f}MB) may take a long time to process[/yellow]"
            )

        model = model or self.config.transcription.default_model
        self.logger.info(f"Using transcription model: {model}")

        # Validate model and API key before processing
        try:
            if not self.transcriber.validate_model(model):
                error_msg = f"Model '{model}' is not available or properly configured"
                self.logger.error(error_msg, model=model)
                raise PipelineError(error_msg)
        except Exception as e:
            error_msg = f"Failed to validate model '{model}': {e}"
            self.logger.error(error_msg, model=model, error=str(e))
            raise PipelineError(error_msg)

        file_id = create_file_id(audio_file)
        self.logger.info(f"Generated file ID: {file_id}")

        # Check if already processing
        existing = self.state_manager.get_file_status(file_id)
        if existing and existing["status"] == "processing":
            error_msg = f"File {file_id} is already being processed"
            self.logger.warning(error_msg, file_id=file_id, status=existing["status"])
            raise PipelineError(error_msg)

        # Start processing
        self.logger.info(f"Starting processing for file {file_id}")
        self.state_manager.start_processing(file_id, str(audio_file))

        try:
            with UnifiedProgressTracker(self.console) as tracker:
                # Phase 1: Audio Processing
                self.logger.info("Starting audio processing phase", file_id=file_id)
                tracker.add_task("processing", f"Processing {audio_file.name}", 100)

                process_output = self.config.processed_path / file_id
                ensure_directory(process_output)

                # Process audio file
                start_time = time.time()
                metadata = self.audio_processor.process_file(audio_file, process_output)
                processing_time = time.time() - start_time

                self.logger.info(
                    "Audio processing completed",
                    file_id=file_id,
                    chunks_created=len(metadata.chunks),
                    duration=metadata.audio_info.get("duration", 0),
                    processing_time_seconds=round(processing_time, 2)
                )

                # Save processing metadata
                metadata.save(process_output / "processing_metadata.json")

                # Create manifest for transcription
                manifest_path = MetadataManager.create_manifest(metadata, process_output)

                tracker.finish_task("processing")
                self.state_manager.update_stage(
                    file_id,
                    "processed",
                    {
                        "chunks": len(metadata.chunks),
                        "duration": metadata.audio_info.get("duration", 0),
                        "processing_time": processing_time,
                    },
                )

                # Phase 2: Transcription
                if self.config.transcription.chunk_processing and metadata.chunks:
                    self.logger.info(
                        "Starting transcription phase", 
                        file_id=file_id, 
                        chunks_to_transcribe=len(metadata.chunks),
                        model=model
                    )
                    tracker.add_task(
                        "transcribing",
                        f"Transcribing {len(metadata.chunks)} chunks",
                        len(metadata.chunks),
                    )

                    transcript_output = self.config.transcribed_path / file_id
                    ensure_directory(transcript_output)

                    # Transcribe chunks
                    start_time = time.time()
                    result = await self.transcriber.transcribe_chunks(
                        metadata,
                        model,
                        transcript_output,
                        progress_callback=lambda: tracker.update_task("transcribing", 1),
                    )
                    transcription_time = time.time() - start_time

                    self.logger.info(
                        "Transcription completed",
                        file_id=file_id,
                        chunks_transcribed=len(metadata.chunks),
                        transcription_time_seconds=round(transcription_time, 2),
                        model=model
                    )

                    tracker.finish_task("transcribing")
                    self.state_manager.update_stage(
                        file_id,
                        "transcribed",
                        {
                            "model": model,
                            "chunks_transcribed": len(metadata.chunks),
                            "transcription_time": transcription_time,
                        },
                    )

                self.state_manager.complete_processing(file_id)
                
                total_time = time.time() - start_time
                self.logger.info(
                    "Pipeline processing completed successfully",
                    file_id=file_id,
                    total_time_seconds=round(total_time, 2),
                    chunks_processed=len(metadata.chunks)
                )

                return {
                    "file_id": file_id,
                    "status": "completed",
                    "processing_metadata": metadata.to_dict(),
                    "transcription_result": result if "result" in locals() else None,
                    "total_time": total_time,
                }

        except Exception as e:
            self.logger.error(
                f"Pipeline failed for {audio_file.name}",
                file_id=file_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            self.state_manager.mark_failed(file_id, str(e))
            raise PipelineError(f"Pipeline failed for {audio_file.name}: {e}")

    async def process_batch(
        self,
        audio_files: List[Path],
        model: Optional[str] = None,
        max_concurrent: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Process multiple files with concurrency control"""
        max_concurrent = max_concurrent or self.config.transcription.max_concurrent
        self.logger.info(
            "Starting batch processing",
            total_files=len(audio_files),
            max_concurrent=max_concurrent,
            model=model or self.config.transcription.default_model
        )
        
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(file: Path):
            async with semaphore:
                try:
                    return await self.process_file(file, model)
                except Exception as e:
                    file_id = create_file_id(file)
                    self.logger.error(
                        f"Error processing {file.name}",
                        file_id=file_id,
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    self.console.print(f"[red]Error processing {file.name}: {e}[/red]")
                    return {"file_id": file_id, "status": "failed", "error": str(e)}

        start_time = time.time()
        tasks = [process_with_semaphore(file) for file in audio_files]
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        successful = len([r for r in results if r.get("status") == "completed"])
        failed = len([r for r in results if r.get("status") == "failed"])
        
        self.logger.info(
            "Batch processing completed",
            total_files=len(audio_files),
            successful=successful,
            failed=failed,
            total_time_seconds=round(total_time, 2)
        )
        
        return results

    def resume_failed(self) -> List[Dict[str, Any]]:
        """Get list of failed files that can be resumed"""
        return self.state_manager.get_failed_files()

    def get_status(self) -> Dict[str, Any]:
        """Get overall pipeline status"""
        return self.state_manager.get_pipeline_summary()

    def cleanup_workspace(self, keep_transcribed: bool = True):
        """Clean up intermediate files"""
        self.logger.info("Starting workspace cleanup", keep_transcribed=keep_transcribed)
        
        if not keep_transcribed:
            # Remove all processed files
            removed_count = 0
            for item in self.config.workspace.processed_path.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                    removed_count += 1
            self.logger.info(f"Removed {removed_count} processed file directories")

        # Clean empty directories
        from neuravox.shared.file_utils import cleanup_empty_directories

        cleanup_empty_directories(self.config.workspace.base_path)
        self.logger.info("Workspace cleanup completed")

