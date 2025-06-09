#!/usr/bin/env python3

"""
Audio Splitter with Metadata and Multiple Output Formats
Integrates metadata generation and output capabilities
"""

import time
from pathlib import Path
from math import ceil
from typing import List, Tuple, Optional, Callable, Dict, Any
from datetime import datetime

import numpy as np
import librosa
import soundfile as sf

# Import our metadata and output capabilities
from neuravox.processor.metadata_output import AudioMetadata, OutputManager, export_with_metadata

# Import shared components for pipeline mode
from neuravox.shared.metadata import ProcessingMetadata, ChunkMetadata
from neuravox.shared.file_utils import create_file_id



class AudioProcessor:
    """Audio processor with metadata and multiple output formats"""
    
    def __init__(self, 
                 sample_rate: int = 22050,
                 chunk_duration: float = 30.0,
                 silence_threshold: float = 0.01,
                 min_silence_duration: float = 25.0,
                 min_chunk_duration: float = 5.0,
                 keep_silence: float = 1.0,
                 create_metadata: bool = True,
                 output_format: str = 'wav',
                 preserve_timestamps: bool = True,
                 pipeline_mode: bool = False):
        
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.silence_threshold = silence_threshold
        self.min_silence_duration = min_silence_duration
        self.min_chunk_duration = min_chunk_duration
        self.keep_silence = keep_silence
        self.create_metadata = create_metadata
        self.output_format = output_format
        self.preserve_timestamps = preserve_timestamps
        self.pipeline_mode = pipeline_mode
        self.cancelled = False
    
    def _detect_silence_in_chunk(self, y: np.ndarray, chunk_start: float, chunk_end: float) -> List[Tuple[float, float]]:
        """Detect silence within a single audio chunk"""
        if len(y) == 0:
            return []
        
        # Calculate RMS energy
        hop_length = 512
        frame_length = 2048
        
        if len(y) < frame_length:
            # For very short chunks, check overall amplitude
            avg_amplitude = np.mean(np.abs(y))
            if avg_amplitude < self.silence_threshold:
                return [(chunk_start, chunk_end)]
            else:
                return []
        
        # Calculate RMS energy for longer chunks
        rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
        
        # Create time array for this chunk
        n_frames = len(rms)
        times = np.linspace(chunk_start, chunk_end, n_frames)
        
        # Find silence regions
        silence_mask = rms < self.silence_threshold
        
        if not np.any(silence_mask):
            return []
        
        # Find continuous silence segments
        silence_diff = np.diff(np.concatenate(([False], silence_mask, [False])).astype(int))
        silence_starts_idx = np.where(silence_diff == 1)[0]
        silence_ends_idx = np.where(silence_diff == -1)[0]
        
        silence_segments = []
        for start_idx, end_idx in zip(silence_starts_idx, silence_ends_idx):
            if start_idx < len(times) and end_idx <= len(times):
                silence_start = times[start_idx] if start_idx < len(times) else chunk_start
                silence_end = times[end_idx-1] if end_idx <= len(times) else chunk_end
                
                # Check if silence is long enough
                if silence_end - silence_start >= self.min_silence_duration:
                    silence_segments.append((silence_start, silence_end))
        
        return silence_segments
    
    def _merge_silence_segments(self, silence_segments: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Merge overlapping or adjacent silence segments"""
        if not silence_segments:
            return []
        
        # Sort by start time
        silence_segments.sort()
        merged = []
        current_start, current_end = silence_segments[0]
        
        for start, end in silence_segments[1:]:
            if start <= current_end + 1.0:  # Merge if within 1 second
                current_end = max(current_end, end)
            else:
                merged.append((current_start, current_end))
                current_start, current_end = start, end
        
        merged.append((current_start, current_end))
        return merged
    
    def _detect_silence_simple(self, input_file: Path, duration: float) -> List[Tuple[float, float]]:
        """Simple silence detection for pipeline mode"""
        # Load full audio file
        y, sr = librosa.load(str(input_file), sr=self.sample_rate)
        
        # Calculate RMS energy
        hop_length = 512
        frame_length = 2048
        rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
        
        # Create time array
        times = librosa.frames_to_time(range(len(rms)), sr=sr, hop_length=hop_length)
        
        # Find silence regions
        silence_mask = rms < self.silence_threshold
        
        if not np.any(silence_mask):
            return []
        
        # Find continuous silence segments
        silence_diff = np.diff(np.concatenate(([False], silence_mask, [False])).astype(int))
        silence_starts_idx = np.where(silence_diff == 1)[0]
        silence_ends_idx = np.where(silence_diff == -1)[0]
        
        silence_segments = []
        for start_idx, end_idx in zip(silence_starts_idx, silence_ends_idx):
            if start_idx < len(times) and end_idx <= len(times):
                silence_start = times[start_idx]
                silence_end = times[end_idx-1] if end_idx <= len(times) else duration
                
                # Check if silence is long enough
                if silence_end - silence_start >= self.min_silence_duration:
                    silence_segments.append((silence_start, silence_end))
        
        return self._merge_silence_segments(silence_segments)
    
    def _create_chunks_simple(self, silence_segments: List[Tuple[float, float]], duration: float) -> List[Tuple[float, float]]:
        """Create audio chunks between silence gaps"""
        audio_chunks = []
        
        if silence_segments:
            # Create chunks between silence gaps
            chunk_start = 0.0
            for silence_start, silence_end in silence_segments:
                # Add chunk before silence (with keep_silence buffer)
                chunk_end = silence_start + self.keep_silence
                if chunk_end - chunk_start >= self.min_chunk_duration:
                    audio_chunks.append((chunk_start, chunk_end))
                
                # Next chunk starts after silence (with keep_silence buffer)
                chunk_start = silence_end - self.keep_silence
            
            # Add final chunk if significant
            if duration - chunk_start >= self.min_chunk_duration:
                audio_chunks.append((chunk_start, duration))
        else:
            # No silence found - treat as single file
            audio_chunks = [(0.0, duration)]
        
        # Filter chunks by minimum duration
        return [(start, end) for start, end in audio_chunks 
               if end - start >= self.min_chunk_duration]
    
    def process_file(self, input_file: Path, output_dir: Path, 
                     progress_callback: Optional[Callable] = None) -> ProcessingMetadata:
        """
        Process file in pipeline mode, returning structured metadata
        
        Args:
            input_file: Path to audio file
            output_dir: Directory for output chunks
            progress_callback: Optional callback for progress updates
            
        Returns:
            ProcessingMetadata object with all chunk information
        """
        if not self.pipeline_mode:
            raise RuntimeError("process_file requires pipeline_mode=True")
        
        start_time = time.time()
        file_id = create_file_id(input_file)
        
        # Get audio metadata
        duration = librosa.get_duration(path=str(input_file))
        y, sr = librosa.load(str(input_file), sr=None, duration=1.0)
        
        audio_info = {
            "duration": duration,
            "sample_rate": int(sr),
            "file_size": input_file.stat().st_size,
            "format": input_file.suffix.lower(),
            "channels": 1 if y.ndim == 1 else y.shape[0]
        }
        
        # Detect silence using simple approach for pipeline mode
        silence_segments = self._detect_silence_simple(input_file, duration)
        
        # Create audio chunks between silence gaps
        audio_chunks = self._create_chunks_simple(silence_segments, duration)
        
        # Export chunks and collect metadata
        chunk_metadata_list = []
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set output format to FLAC for transcription optimization
        self.output_format = 'flac'
        
        # If chunking occurred (multiple chunks), save full file and organize chunks in subdirectory
        if len(audio_chunks) > 1:
            # Save full file as FLAC
            full_file_path = output_dir / "full-file.flac"
            try:
                # Load full audio file and convert to 16kHz mono FLAC
                y_full, sr_full = librosa.load(str(input_file), sr=16000, mono=True)
                sf.write(str(full_file_path), y_full, 16000, format='FLAC')
                if not self.pipeline_mode:
                    print(f"   ✓ Saved full audio file: {full_file_path.name}")
            except Exception as e:
                if not self.pipeline_mode:
                    print(f"   ⚠️  Failed to save full audio file: {e}")
            
            # Create chunks subdirectory for organized storage
            chunks_dir = output_dir / "chunks"
            chunks_dir.mkdir(exist_ok=True)
        else:
            # Single chunk - no need for subdirectory or full file
            chunks_dir = output_dir
        
        for idx, (start, end) in enumerate(audio_chunks):
            if progress_callback:
                progress_callback()
            
            # Load chunk audio
            y, sr = librosa.load(str(input_file), sr=16000, mono=True,
                               offset=start, duration=end-start)
            
            # Create output filename in appropriate directory
            chunk_file = chunks_dir / f"chunk_{idx:03d}.flac"
            
            # Save chunk
            sf.write(str(chunk_file), y, sr, format='FLAC')
            
            # Create chunk metadata
            chunk_meta = ChunkMetadata(
                chunk_index=idx,
                total_chunks=len(audio_chunks),
                start_time=start,
                end_time=end,
                duration=end - start,
                file_path=chunk_file,
                source_file=input_file
            )
            chunk_metadata_list.append(chunk_meta)
        
        # Create processing metadata
        processing_params = {
            "silence_threshold": self.silence_threshold,
            "min_silence_duration": self.min_silence_duration,
            "min_chunk_duration": self.min_chunk_duration,
            "keep_silence": self.keep_silence,
            "output_format": self.output_format
        }
        
        metadata = ProcessingMetadata(
            file_id=file_id,
            original_file=input_file,
            processed_at=datetime.now(),
            processing_time=time.time() - start_time,
            chunks=chunk_metadata_list,
            audio_info=audio_info,
            processing_params=processing_params
        )
        
        return metadata

    def convert_file(self, input_file: Path, output_file: Path, 
                     format: str = 'flac', quality: Optional[str] = None,
                     sample_rate: Optional[int] = None, normalize: bool = False) -> Dict[str, Any]:
        """
        Convert audio file to different format with optional parameters
        
        Args:
            input_file: Path to input audio file
            output_file: Path for output file
            format: Target format (flac, mp3, wav, etc.)
            quality: Quality setting for lossy formats
            sample_rate: Target sample rate (None to keep original)
            normalize: Whether to normalize audio
            
        Returns:
            Dictionary with conversion metadata
        """
        start_time = time.time()
        
        try:
            # Load audio file
            y, sr = librosa.load(str(input_file), sr=sample_rate, mono=True)
            
            # Normalize if requested
            if normalize:
                y = librosa.util.normalize(y)
            
            # Determine output format parameters
            if format.lower() == 'flac':
                output_format = 'FLAC'
                subtype = 'PCM_16'
            elif format.lower() == 'wav':
                output_format = 'WAV'
                subtype = 'PCM_16'
            elif format.lower() == 'mp3':
                output_format = 'MP3'
                subtype = quality or 'MP3'
            else:
                output_format = format.upper()
                subtype = None
            
            # Create output directory if needed
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write converted file
            sf.write(str(output_file), y, sr, format=output_format, subtype=subtype)
            
            conversion_time = time.time() - start_time
            
            # Get file info
            input_size = input_file.stat().st_size
            output_size = output_file.stat().st_size
            
            return {
                "status": "success",
                "input_file": str(input_file),
                "output_file": str(output_file),
                "format": format,
                "sample_rate": sr,
                "duration": len(y) / sr,
                "conversion_time": conversion_time,
                "input_size": input_size,
                "output_size": output_size,
                "compression_ratio": output_size / input_size if input_size > 0 else 1.0,
                "normalized": normalize
            }
            
        except Exception as e:
            return {
                "status": "error",
                "input_file": str(input_file),
                "output_file": str(output_file),
                "error": str(e),
                "conversion_time": time.time() - start_time
            }





