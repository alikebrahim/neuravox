from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
import asyncio
import datetime
import json
import librosa

from neuravox.shared.config import UnifiedConfig
from neuravox.shared.logging_config import get_engine_logger
from neuravox.transcriber.models.google_ai import GoogleAIModel
from neuravox.transcriber.models.openai import OpenAIModel
from neuravox.transcriber.models.whisper_local import LocalWhisperModel
from neuravox.shared.metadata import ProcessingMetadata, TranscriptionMetadata


class AudioTranscriber:
    """Core audio transcription engine."""
    
    def __init__(self, config: Optional[UnifiedConfig] = None):
        self.config = config or UnifiedConfig()
        self.logger = get_engine_logger()
        self._models = {}
        
        self.logger.info("Transcription engine initialized")
    
    def get_model(self, model_key: str):
        """Get or create a model instance."""
        if model_key not in self._models:
            self.logger.info(f"Loading model: {model_key}")
            model_config = self.config.get_model(model_key)
            if not model_config:
                error_msg = f"Model '{model_key}' not found in configuration"
                self.logger.error(error_msg, model_key=model_key)
                raise ValueError(error_msg)
            
            # Prepare model kwargs including system prompt if configured
            model_kwargs = model_config.parameters.copy()
            if model_config.system_prompt:
                model_kwargs['system_prompt'] = model_config.system_prompt
            
            # Create model instance based on provider
            # API keys are now handled by the model classes directly from environment
            try:
                if model_config.provider == "google":
                    self._models[model_key] = GoogleAIModel(
                        model_id=model_config.model_id,
                        **model_kwargs
                    )
                elif model_config.provider == "openai":
                    self._models[model_key] = OpenAIModel(
                        model_id=model_config.model_id,
                        **model_kwargs
                    )
                elif model_config.provider == "whisper-local":
                    self._models[model_key] = LocalWhisperModel(
                        model_id=model_config.model_id,
                        device=model_config.device,
                        **model_kwargs
                    )
                else:
                    error_msg = f"Unsupported provider: {model_config.provider}"
                    self.logger.error(error_msg, provider=model_config.provider, model_key=model_key)
                    raise ValueError(error_msg)
                
                self.logger.info(
                    f"Model loaded successfully",
                    model_key=model_key,
                    provider=model_config.provider,
                    model_id=model_config.model_id
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to load model {model_key}",
                    model_key=model_key,
                    provider=model_config.provider,
                    error=str(e),
                    exc_info=True
                )
                raise
        
        return self._models[model_key]
    
    async def transcribe_file(
        self, 
        audio_path: Path, 
        model_key: str, 
        output_dir: Path
    ) -> Dict[str, Any]:
        """
        Transcribe a single audio file.
        
        Args:
            audio_path: Path to the audio file
            model_key: Key of the model to use
            output_dir: Directory to save the transcription
            
        Returns:
            Dictionary with transcription results and metadata
        """
        self.logger.info(f"Starting transcription", audio_file=str(audio_path), model=model_key)
        
        # Validate inputs
        if not audio_path.exists():
            error_msg = f"Audio file not found: {audio_path}"
            self.logger.error(error_msg, audio_path=str(audio_path))
            raise FileNotFoundError(error_msg)
        
        # Get model and validate it's available before creating any directories
        model = self.get_model(model_key)
        
        if not model.is_available():
            error_msg = f"Model '{model_key}' is not available"
            self.logger.error(error_msg, model_key=model_key)
            raise RuntimeError(error_msg)
        
        # Get audio metadata using librosa
        audio_metadata = self._get_audio_metadata(audio_path)
        
        # Record start time
        start_time = datetime.datetime.now()
        
        try:
            # Perform transcription
            transcription = await model.transcribe(audio_path)
            
            # Record end time
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Only create output directory after successful transcription
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Prepare output filename
            output_filename = f"{audio_path.stem}_transcript.md"
            output_file = output_dir / output_filename
            
            # Format transcription as Markdown
            markdown_content = self._format_transcription_as_markdown(
                transcription=transcription,
                audio_path=audio_path,
                model_name=model.name,
                model_key=model_key,
                start_time=start_time,
                duration=duration,
                audio_metadata=audio_metadata
            )
            
            # Save transcription
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            # Prepare metadata
            metadata = {
                "source_file": str(audio_path),
                "output_file": str(output_file),
                "model": model_key,
                "model_name": model.name,
                "transcription_time": duration,
                "timestamp": start_time.isoformat(),
                "audio_metadata": audio_metadata,
                "character_count": len(transcription),
                "word_count": len(transcription.split())
            }
            
            # Save metadata
            metadata_file = output_dir / f"{audio_path.stem}_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            return {
                "success": True,
                "transcription": transcription,
                "output_file": output_file,
                "metadata_file": metadata_file,
                "metadata": metadata
            }
            
        except Exception as e:
            # Don't create directories or files on failure - just re-raise the exception
            raise RuntimeError(f"Transcription failed: {e}")
    
    def _get_audio_metadata(self, audio_path: Path) -> Dict[str, Any]:
        """Extract metadata from audio file using librosa."""
        try:
            # Get duration without loading full audio
            duration = librosa.get_duration(path=str(audio_path))
            
            # Load a small sample to get sample rate
            y, sr = librosa.load(str(audio_path), sr=None, duration=1.0)
            
            # Get file size
            file_size = audio_path.stat().st_size
            
            return {
                "duration_seconds": float(duration),
                "sample_rate": int(sr),
                "file_size_bytes": file_size,
                "file_format": audio_path.suffix.lower(),
                "channels": 1 if y.ndim == 1 else y.shape[0]
            }
            
        except Exception as e:
            return {
                "error": f"Failed to extract metadata: {e}",
                "file_size_bytes": audio_path.stat().st_size if audio_path.exists() else 0,
                "file_format": audio_path.suffix.lower()
            }
    
    async def transcribe_batch(
        self, 
        audio_files: list[Path], 
        model_key: str, 
        output_dir: Path,
        max_concurrent: int = 3
    ) -> list[Dict[str, Any]]:
        """
        Transcribe multiple audio files concurrently.
        
        Args:
            audio_files: List of audio file paths
            model_key: Key of the model to use
            output_dir: Directory to save transcriptions
            max_concurrent: Maximum number of concurrent transcriptions
            
        Returns:
            List of transcription results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def transcribe_with_semaphore(audio_file: Path) -> Dict[str, Any]:
            async with semaphore:
                try:
                    return await self.transcribe_file(audio_file, model_key, output_dir)
                except Exception as e:
                    return {
                        "success": False,
                        "source_file": str(audio_file),
                        "error": str(e)
                    }
        
        # Run transcriptions concurrently
        tasks = [transcribe_with_semaphore(audio_file) for audio_file in audio_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    def validate_model(self, model_key: str) -> bool:
        """Validate that a model is properly configured and available."""
        self.logger.info(f"Validating model: {model_key}")
        try:
            model = self.get_model(model_key)
            is_available = model.is_available()
            if is_available:
                self.logger.info(f"Model validation successful", model_key=model_key)
            else:
                self.logger.warning(f"Model validation failed: not available", model_key=model_key)
            return is_available
        except Exception as e:
            self.logger.error(f"Model validation failed with exception", model_key=model_key, error=str(e))
            return False
    
    def get_audio_info(self, audio_path: Path) -> Dict[str, Any]:
        """Get detailed information about an audio file."""
        if not audio_path.exists():
            return {"error": "File not found"}
        
        metadata = self._get_audio_metadata(audio_path)
        
        # Add file information
        stat = audio_path.stat()
        metadata.update({
            "filename": audio_path.name,
            "full_path": str(audio_path),
            "created": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
        
        return metadata
    
    def _format_transcription_as_markdown(
        self,
        transcription: str,
        audio_path: Path,
        model_name: str,
        model_key: str,
        start_time: datetime.datetime,
        duration: float,
        audio_metadata: Dict[str, Any]
    ) -> str:
        """Format transcription content as Markdown."""
        
        # Format duration nicely
        audio_duration = audio_metadata.get("duration_seconds", 0)
        if audio_duration > 3600:
            duration_str = f"{audio_duration / 3600:.1f} hours"
        elif audio_duration > 60:
            duration_str = f"{audio_duration / 60:.1f} minutes"
        else:
            duration_str = f"{audio_duration:.1f} seconds"
        
        # Format transcription time
        if duration > 60:
            transcription_time_str = f"{duration / 60:.1f} minutes"
        else:
            transcription_time_str = f"{duration:.1f} seconds"
        
        # Format file size
        file_size = audio_metadata.get("file_size_bytes", 0)
        if file_size > 1024 * 1024:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"
        elif file_size > 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        else:
            size_str = f"{file_size} bytes"
        
        # Build Markdown content
        markdown_content = f"""# Transcription: {audio_path.name}

**Source File:** `{audio_path.name}`  
**Model:** {model_name} (`{model_key}`)  
**Audio Duration:** {duration_str}  
**File Size:** {size_str}  
**Sample Rate:** {audio_metadata.get("sample_rate", "Unknown")} Hz  
**Format:** {audio_metadata.get("file_format", "Unknown")}  
**Transcribed:** {start_time.strftime("%Y-%m-%d %H:%M:%S")}  
**Processing Time:** {transcription_time_str}  

---

## Transcription

{transcription.strip()}

---

*Generated by Audio Transcriber using {model_name}*  
*Processing completed in {transcription_time_str} on {start_time.strftime("%B %d, %Y at %H:%M:%S")}*
"""
        
        return markdown_content
    
    async def transcribe_chunks(
        self,
        processing_metadata: ProcessingMetadata,
        model_key: str,
        output_dir: Path,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio chunks based on processing metadata
        
        Args:
            processing_metadata: Metadata from audio processing stage
            model_key: Key of the model to use
            output_dir: Directory to save transcriptions
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with combined transcription and metadata
        """
        # Validate model availability
        model = self.get_model(model_key)
        if not model.is_available():
            raise RuntimeError(f"Model '{model_key}' is not available")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Transcribe each chunk
        chunk_transcriptions = []
        start_time = datetime.datetime.now()
        
        for chunk in processing_metadata.chunks:
            if not chunk.file_path.exists():
                raise FileNotFoundError(f"Chunk file not found: {chunk.file_path}")
            
            try:
                # Transcribe chunk
                transcription = await model.transcribe(chunk.file_path)
                
                chunk_transcriptions.append({
                    "chunk_index": chunk.chunk_index,
                    "start_time": chunk.start_time,
                    "end_time": chunk.end_time,
                    "text": transcription
                })
                
                # Save individual chunk transcription
                chunk_output = output_dir / f"chunk_{chunk.chunk_index:03d}_transcript.txt"
                with open(chunk_output, 'w', encoding='utf-8') as f:
                    f.write(transcription)
                
                # Update progress
                if progress_callback:
                    progress_callback()
                    
            except Exception as e:
                raise RuntimeError(f"Failed to transcribe chunk {chunk.chunk_index}: {e}")
        
        # Combine transcriptions
        combined_text = "\n\n".join([
            chunk["text"] for chunk in sorted(chunk_transcriptions, key=lambda x: x["chunk_index"])
        ])
        
        # Calculate statistics
        end_time = datetime.datetime.now()
        transcription_time = (end_time - start_time).total_seconds()
        word_count = len(combined_text.split())
        char_count = len(combined_text)
        
        # Save combined transcription as markdown
        combined_output = output_dir / f"{processing_metadata.file_id}_transcript.md"
        
        # Format combined transcription with metadata
        markdown_content = self._format_chunks_transcription_as_markdown(
            processing_metadata=processing_metadata,
            chunk_transcriptions=chunk_transcriptions,
            combined_text=combined_text,
            model_name=model.name,
            model_key=model_key,
            start_time=start_time,
            transcription_time=transcription_time
        )
        
        with open(combined_output, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        # Save transcription metadata
        transcription_metadata = TranscriptionMetadata(
            file_id=processing_metadata.file_id,
            model_used=model_key,
            transcribed_at=start_time,
            transcription_time=transcription_time,
            word_count=word_count,
            char_count=char_count,
            chunks_transcribed=len(processing_metadata.chunks),
            combined=True
        )
        
        metadata_file = output_dir / f"{processing_metadata.file_id}_transcription_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(transcription_metadata.to_dict(), f, indent=2)
        
        # Save chunk details
        chunks_file = output_dir / f"{processing_metadata.file_id}_chunks.json"
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump(chunk_transcriptions, f, indent=2)
        
        return {
            "success": True,
            "transcription": combined_text,
            "output_file": combined_output,
            "metadata_file": metadata_file,
            "chunks_file": chunks_file,
            "metadata": transcription_metadata.to_dict(),
            "chunks": chunk_transcriptions
        }
    
    def _format_chunks_transcription_as_markdown(
        self,
        processing_metadata: ProcessingMetadata,
        chunk_transcriptions: List[Dict[str, Any]],
        combined_text: str,
        model_name: str,
        model_key: str,
        start_time: datetime.datetime,
        transcription_time: float
    ) -> str:
        """Format chunk-based transcription as Markdown."""
        
        # Format duration
        audio_duration = processing_metadata.audio_info.get("duration", 0)
        if audio_duration > 3600:
            duration_str = f"{audio_duration / 3600:.1f} hours"
        elif audio_duration > 60:
            duration_str = f"{audio_duration / 60:.1f} minutes"
        else:
            duration_str = f"{audio_duration:.1f} seconds"
        
        # Format transcription time
        if transcription_time > 60:
            transcription_time_str = f"{transcription_time / 60:.1f} minutes"
        else:
            transcription_time_str = f"{transcription_time:.1f} seconds"
        
        # Format file size
        file_size = processing_metadata.audio_info.get("file_size", 0)
        if file_size > 1024 * 1024:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"
        elif file_size > 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        else:
            size_str = f"{file_size} bytes"
        
        # Build Markdown content
        markdown_content = f"""# Transcription: {processing_metadata.original_file.name}

**Source File:** `{processing_metadata.original_file.name}`  
**File ID:** `{processing_metadata.file_id}`  
**Model:** {model_name} (`{model_key}`)  
**Audio Duration:** {duration_str}  
**File Size:** {size_str}  
**Sample Rate:** {processing_metadata.audio_info.get("sample_rate", "Unknown")} Hz  
**Format:** {processing_metadata.audio_info.get("format", "Unknown")}  
**Chunks Processed:** {len(processing_metadata.chunks)}  
**Transcribed:** {start_time.strftime("%Y-%m-%d %H:%M:%S")}  
**Processing Time:** {transcription_time_str}  

---

## Processing Information

**Silence Detection Threshold:** {processing_metadata.processing_params.get("silence_threshold", "N/A")}  
**Minimum Silence Duration:** {processing_metadata.processing_params.get("min_silence_duration", "N/A")}s  
**Audio Processing Time:** {processing_metadata.processing_time:.1f}s  

---

## Combined Transcription

{combined_text.strip()}

---

## Chunk Details

"""
        
        # Add chunk breakdown
        for chunk in chunk_transcriptions:
            start_min = chunk["start_time"] / 60
            end_min = chunk["end_time"] / 60
            markdown_content += f"\n### Chunk {chunk['chunk_index'] + 1} ({start_min:.1f}m - {end_min:.1f}m)\n\n"
            markdown_content += f"{chunk['text'].strip()}\n"
        
        markdown_content += f"""
---

*Generated by Audio Workflow Platform using {model_name}*  
*Processing completed in {transcription_time_str} on {start_time.strftime("%B %d, %Y at %H:%M:%S")}*
"""
        
        return markdown_content