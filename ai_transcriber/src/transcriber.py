from pathlib import Path
from typing import Dict, Any, Optional
import asyncio
import datetime
import json
import librosa

from .config import config_manager
from .models.google_ai import GoogleAIModel
from .models.openai import OpenAIModel
from .models.ollama import OllamaModel


class AudioTranscriber:
    """Core audio transcription engine."""
    
    def __init__(self):
        self.config = config_manager.config
        self._models = {}
    
    def get_model(self, model_key: str):
        """Get or create a model instance."""
        if model_key not in self._models:
            model_config = self.config.models.get(model_key)
            if not model_config:
                raise ValueError(f"Model '{model_key}' not found in configuration")
            
            # Prepare model kwargs including system prompt if configured
            model_kwargs = model_config.parameters.copy()
            if model_config.system_prompt:
                model_kwargs['system_prompt'] = model_config.system_prompt
            
            # Create model instance based on provider
            if model_config.provider == "google":
                self._models[model_key] = GoogleAIModel(
                    model_id=model_config.model_id,
                    api_key=model_config.api_key,
                    **model_kwargs
                )
            elif model_config.provider == "openai":
                self._models[model_key] = OpenAIModel(
                    model_id=model_config.model_id,
                    api_key=model_config.api_key,
                    **model_kwargs
                )
            elif model_config.provider == "ollama":
                self._models[model_key] = OllamaModel(
                    model_id=model_config.model_id,
                    api_url=model_config.api_url or "http://localhost:11434",
                    **model_kwargs
                )
            else:
                raise ValueError(f"Unsupported provider: {model_config.provider}")
        
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
        # Validate inputs
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Get model and validate it's available before creating any directories
        model = self.get_model(model_key)
        
        if not model.is_available():
            raise RuntimeError(f"Model '{model_key}' is not available")
        
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
        try:
            model = self.get_model(model_key)
            return model.is_available()
        except Exception:
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