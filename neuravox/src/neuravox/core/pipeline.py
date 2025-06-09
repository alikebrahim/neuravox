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
from .state_manager import StateManager
from .exceptions import PipelineError
from rich.console import Console

class AudioPipeline:
    """Main pipeline orchestrator"""
    
    def __init__(self, config: Optional[UnifiedConfig] = None):
        self.config = config or UnifiedConfig()
        self.console = Console()
        self.state_manager = StateManager(self.config.workspace.base_path)
        
        # Initialize modules with pipeline mode
        self.audio_processor = AudioProcessor(
            silence_threshold=self.config.processing.silence_threshold,
            min_silence_duration=self.config.processing.min_silence_duration,
            pipeline_mode=True
        )
        self.transcriber = AudioTranscriber()
    
    async def process_file(self, 
                         audio_file: Path,
                         model: Optional[str] = None) -> Dict[str, Any]:
        """
        Process single audio file through full pipeline
        
        Args:
            audio_file: Path to audio file
            model: Transcription model (uses default if None)
            
        Returns:
            Complete processing results
        """
        # Validate input file
        if not audio_file.exists():
            raise PipelineError(f"Audio file not found: {audio_file}")
        
        if not audio_file.is_file():
            raise PipelineError(f"Path is not a file: {audio_file}")
        
        # Check if it's an audio file
        audio_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.opus', '.wma', '.aac', '.mp4'}
        if audio_file.suffix.lower() not in audio_extensions:
            raise PipelineError(f"Unsupported file format: {audio_file.suffix}")
        
        # Check file size (warn if very large)
        file_size_mb = audio_file.stat().st_size / (1024 * 1024)
        if file_size_mb > 1000:  # 1GB
            self.console.print(f"[yellow]Warning: Large file ({file_size_mb:.1f}MB) may take a long time to process[/yellow]")
        
        model = model or self.config.transcription.default_model
        
        # Validate model and API key before processing
        try:
            if not self.transcriber.validate_model(model):
                raise PipelineError(f"Model '{model}' is not available or properly configured")
        except Exception as e:
            raise PipelineError(f"Failed to validate model '{model}': {e}")
        
        file_id = create_file_id(audio_file)
        
        # Check if already processing
        existing = self.state_manager.get_file_status(file_id)
        if existing and existing['status'] == 'processing':
            raise PipelineError(f"File {file_id} is already being processed")
        
        # Start processing
        self.state_manager.start_processing(file_id, str(audio_file))
        
        try:
            with UnifiedProgressTracker(self.console) as tracker:
                # Phase 1: Audio Processing
                tracker.add_task('processing', f"Processing {audio_file.name}", 100)
                
                process_output = self.config.workspace.processed_path / file_id
                ensure_directory(process_output)
                
                # Process audio file
                start_time = time.time()
                metadata = self.audio_processor.process_file(
                    audio_file, 
                    process_output
                )
                processing_time = time.time() - start_time
                
                # Save processing metadata
                metadata.save(process_output / 'processing_metadata.json')
                
                # Create manifest for transcription
                manifest_path = MetadataManager.create_manifest(metadata, process_output)
                
                tracker.finish_task('processing')
                self.state_manager.update_stage(file_id, 'processed', {
                    'chunks': len(metadata.chunks),
                    'duration': metadata.audio_info.get('duration', 0),
                    'processing_time': processing_time
                })
                
                # Phase 2: Transcription
                if self.config.transcription.chunk_processing and metadata.chunks:
                    tracker.add_task('transcribing', 
                                   f"Transcribing {len(metadata.chunks)} chunks", 
                                   len(metadata.chunks))
                    
                    transcript_output = self.config.workspace.transcribed_path / file_id
                    ensure_directory(transcript_output)
                    
                    # Transcribe chunks
                    start_time = time.time()
                    result = await self.transcriber.transcribe_chunks(
                        metadata,
                        model,
                        transcript_output,
                        progress_callback=lambda: tracker.update_task('transcribing', 1)
                    )
                    transcription_time = time.time() - start_time
                    
                    tracker.finish_task('transcribing')
                    self.state_manager.update_stage(file_id, 'transcribed', {
                        'model': model,
                        'chunks_transcribed': len(metadata.chunks),
                        'transcription_time': transcription_time
                    })
                
                self.state_manager.complete_processing(file_id)
                
                return {
                    'file_id': file_id,
                    'status': 'completed',
                    'processing_metadata': metadata.to_dict(),
                    'transcription_result': result if 'result' in locals() else None,
                    'total_time': time.time() - start_time
                }
                
        except Exception as e:
            self.state_manager.mark_failed(file_id, str(e))
            raise PipelineError(f"Pipeline failed for {audio_file.name}: {e}")
    
    async def process_batch(self, 
                          audio_files: List[Path],
                          model: Optional[str] = None,
                          max_concurrent: Optional[int] = None) -> List[Dict[str, Any]]:
        """Process multiple files with concurrency control"""
        max_concurrent = max_concurrent or self.config.transcription.max_concurrent
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(file: Path):
            async with semaphore:
                try:
                    return await self.process_file(file, model)
                except Exception as e:
                    self.console.print(f"[red]Error processing {file.name}: {e}[/red]")
                    return {
                        'file_id': create_file_id(file),
                        'status': 'failed',
                        'error': str(e)
                    }
        
        tasks = [process_with_semaphore(file) for file in audio_files]
        return await asyncio.gather(*tasks)
    
    def resume_failed(self) -> List[Dict[str, Any]]:
        """Get list of failed files that can be resumed"""
        return self.state_manager.get_failed_files()
    
    def get_status(self) -> Dict[str, Any]:
        """Get overall pipeline status"""
        return self.state_manager.get_pipeline_summary()
    
    def cleanup_workspace(self, keep_transcribed: bool = True):
        """Clean up intermediate files"""
        if not keep_transcribed:
            # Remove all processed files
            for item in self.config.workspace.processed_path.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
        
        # Clean empty directories
        from neuravox.shared.file_utils import cleanup_empty_directories
        cleanup_empty_directories(self.config.workspace.base_path)