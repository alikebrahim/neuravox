#!/usr/bin/env python3

"""
Audio Splitter with Metadata and Multiple Output Formats
Integrates metadata generation and output capabilities
"""

import os
import sys
import time
import signal
import threading
import shutil
from pathlib import Path
from math import ceil
from typing import List, Tuple, Optional, Callable, Dict, Any

import numpy as np
import librosa
import soundfile as sf
import psutil
from tqdm import tqdm

# Import our metadata and output capabilities
from metadata_output import AudioMetadata, OutputManager, export_with_metadata


class MemoryMonitor:
    """Monitor memory usage during processing"""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_memory = self.get_current_usage()
        self.peak_memory = self.start_memory
        self.memory_history = []
        
    def get_current_usage(self) -> float:
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / (1024 * 1024)
    
    def update(self) -> float:
        """Update memory tracking and return current usage"""
        current = self.get_current_usage()
        self.peak_memory = max(self.peak_memory, current)
        self.memory_history.append(current)
        return current
    
    def get_increase(self) -> float:
        """Get memory increase from start"""
        return self.get_current_usage() - self.start_memory
    
    def get_efficiency_ratio(self, file_size_mb: float) -> float:
        """Calculate memory efficiency ratio"""
        increase = self.get_increase()
        return file_size_mb / increase if increase > 0 else float('inf')


class ProgressTracker:
    """Track and display processing progress with metadata collection"""
    
    def __init__(self, total_duration: float, chunk_duration: float = 30.0):
        self.total_duration = total_duration
        self.chunk_duration = chunk_duration
        self.total_chunks = ceil(total_duration / chunk_duration)
        self.current_stage = 1
        self.total_stages = 4
        self.current_chunk = 0
        self.processed_time = 0.0
        self.start_time = time.time()
        self.stage_start_time = time.time()
        self.silence_segments = []
        self.memory_monitor = MemoryMonitor()
        self.cancelled = False
        
    def start_stage(self, stage_num: int, stage_name: str):
        """Start a new processing stage"""
        self.current_stage = stage_num
        self.stage_start_time = time.time()
        print(f"\n🔍 Stage {stage_num}/{self.total_stages}: {stage_name}")
        
    def update_chunk_progress(self, chunk_num: int, processed_time: float, 
                            silence_found: int = 0, chunk_info: str = ""):
        """Update progress for current chunk"""
        self.current_chunk = chunk_num
        self.processed_time = processed_time
        
        # Calculate metrics
        progress_pct = (chunk_num / self.total_chunks) * 100
        elapsed = time.time() - self.start_time
        speed = processed_time / elapsed if elapsed > 0 else 0
        memory_mb = self.memory_monitor.update()
        
        # Calculate ETA
        if speed > 0:
            remaining_time = (self.total_duration - processed_time) / speed
            eta_str = f"ETA: {remaining_time/60:.1f}m" if remaining_time > 0 else "ETA: --"
        else:
            eta_str = "ETA: --"
        
        # Display progress
        print(f"   Chunk {chunk_num:2d}/{self.total_chunks} | "
              f"Progress: {progress_pct:5.1f}% | "
              f"Processed: {processed_time/60:5.1f}m | "
              f"Memory: {memory_mb:6.1f}MB")
        
        if chunk_info:
            print(f"   Speed: {speed:6.1f}x realtime | {eta_str} | {chunk_info}")
        else:
            print(f"   Speed: {speed:6.1f}x realtime | {eta_str}")
            
        if silence_found > 0:
            print(f"   Found: {silence_found} silence gaps")
    
    def add_silence_segment(self, start: float, end: float):
        """Add a detected silence segment"""
        self.silence_segments.append((start, end))
    
    def get_overall_progress(self) -> float:
        """Get overall progress percentage across all stages"""
        stage_weights = [0.05, 0.80, 0.10, 0.05]  # Stage importance weights
        
        if self.current_stage == 1:
            return 0.0
        elif self.current_stage == 2:
            chunk_progress = (self.current_chunk / self.total_chunks) if self.total_chunks > 0 else 0
            return stage_weights[0] + (stage_weights[1] * chunk_progress)
        elif self.current_stage == 3:
            return sum(stage_weights[:2]) + (stage_weights[2] * 0.5)
        else:
            return sum(stage_weights[:3]) + (stage_weights[3] * 1.0)
    
    def show_summary(self, chunks_created: int, output_dir: Path, metadata_report: str = ""):
        """Show final processing summary with metadata"""
        total_time = time.time() - self.start_time
        peak_memory = self.memory_monitor.peak_memory
        memory_increase = self.memory_monitor.get_increase()
        
        print(f"\n✅ Processing Complete!")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Processing speed: {self.total_duration/total_time:.1f}x realtime")
        print(f"   Peak memory: {peak_memory:.1f}MB (+{memory_increase:.1f}MB)")
        print(f"   Silence segments found: {len(self.silence_segments)}")
        print(f"   Audio chunks created: {chunks_created}")
        print(f"   Output directory: {output_dir}")
        
        # Show metadata report if available
        if metadata_report:
            print(f"\n📊 Detailed Report:")
            # Show first few lines of the report
            report_lines = metadata_report.split('\n')
            for line in report_lines[2:12]:  # Skip title and show summary
                if line.strip():
                    print(f"   {line}")
            if len(report_lines) > 12:
                print(f"   ... (see metadata files for complete report)")


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
                 preserve_timestamps: bool = True):
        
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.silence_threshold = silence_threshold
        self.min_silence_duration = min_silence_duration
        self.min_chunk_duration = min_chunk_duration
        self.keep_silence = keep_silence
        self.create_metadata = create_metadata
        self.output_format = output_format
        self.preserve_timestamps = preserve_timestamps
        self.cancelled = False
        
        # Setup signal handler for graceful cancellation
        signal.signal(signal.SIGINT, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print(f"\n⚠️  Cancellation requested... finishing current chunk")
        self.cancelled = True
    
    def process_audio_file(self, input_file: Path, output_dir: Path) -> Dict[str, Any]:
        """
        Process a single audio file with metadata and output options
        """
        try:
            # Stage 1: Audio Metadata Analysis
            progress = self._analyze_metadata(input_file)
            if self.cancelled:
                return self._create_cancelled_result()
            
            # Stage 2: Chunked Silence Detection
            silence_segments = self._detect_silence_chunked(input_file, progress)
            if self.cancelled:
                return self._create_cancelled_result()
            
            # Stage 3: Chunk Assembly and Filtering
            audio_chunks = self._create_audio_chunks(silence_segments, progress.total_duration, progress)
            if self.cancelled:
                return self._create_cancelled_result()
            
            # Stage 4: Export with Metadata
            chunk_count, metadata_report = self._export_chunks(
                input_file, audio_chunks, output_dir, progress, silence_segments
            )
            
            # Show final summary with metadata
            progress.show_summary(chunk_count, output_dir, metadata_report)
            
            return {
                "success": True,
                "chunks_created": chunk_count,
                "total_duration": progress.total_duration,
                "filtered_duration": sum(end - start for start, end in audio_chunks),
                "processing_time": time.time() - progress.start_time,
                "silence_segments": len(silence_segments),
                "output_dir": output_dir,
                "memory_peak": progress.memory_monitor.peak_memory,
                "memory_increase": progress.memory_monitor.get_increase(),
                "metadata_report": metadata_report
            }
            
        except Exception as e:
            print(f"❌ Error processing {input_file.name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "chunks_created": 0,
                "total_duration": 0,
                "processing_time": 0
            }
    
    def _analyze_metadata(self, input_file: Path) -> ProgressTracker:
        """Stage 1: Analyze audio metadata"""
        print(f"\n📁 Loading audio file: {input_file.name}")
        
        # Get file info
        file_size_mb = input_file.stat().st_size / (1024 * 1024)
        duration = librosa.get_duration(path=str(input_file))
        
        print(f"   ✓ Duration: {duration/60:.1f}m | Size: {file_size_mb:.1f}MB")
        
        # Initialize progress tracker
        progress = ProgressTracker(duration, self.chunk_duration)
        progress.start_stage(1, "Audio Metadata Analysis")
        
        print(f"   ✓ Will process in {progress.total_chunks} chunks of {self.chunk_duration}s each")
        print(f"   ✓ Output format: {self.output_format.upper()}")
        if self.create_metadata:
            print(f"   ✓ Metadata generation: enabled")
        
        return progress
    
    def _detect_silence_chunked(self, input_file: Path, progress: ProgressTracker) -> List[Tuple[float, float]]:
        """Stage 2: Detect silence using chunked processing"""
        progress.start_stage(2, f"Silence Detection (threshold: {self.silence_threshold:.3f}, min gap: {self.min_silence_duration}s)")
        
        silence_segments = []
        
        # Process audio in chunks
        for chunk_num in range(1, progress.total_chunks + 1):
            if self.cancelled:
                break
                
            chunk_start = (chunk_num - 1) * self.chunk_duration
            chunk_end = min(chunk_start + self.chunk_duration, progress.total_duration)
            chunk_duration_actual = chunk_end - chunk_start
            
            # Load only this chunk (streaming approach)
            try:
                y, sr = librosa.load(str(input_file), 
                                   sr=self.sample_rate, 
                                   offset=chunk_start, 
                                   duration=chunk_duration_actual)
                
                if len(y) == 0:
                    continue
                
                # Detect silence in this chunk
                chunk_silence = self._detect_silence_in_chunk(y, chunk_start, chunk_end)
                silence_segments.extend(chunk_silence)
                
                # Update progress
                progress.update_chunk_progress(
                    chunk_num, 
                    chunk_end, 
                    len(chunk_silence),
                    f"Silence gaps: {len(chunk_silence)}"
                )
                
            except Exception as e:
                print(f"   ⚠️  Error processing chunk {chunk_num}: {e}")
                continue
        
        # Merge overlapping silence segments
        merged_segments = self._merge_silence_segments(silence_segments)
        
        print(f"   ✓ Found {len(merged_segments)} silence segments >= {self.min_silence_duration}s")
        for i, (start, end) in enumerate(merged_segments, 1):
            print(f"      Silence {i}: {start/60:.1f}m - {end/60:.1f}m ({end-start:.1f}s)")
            progress.add_silence_segment(start, end)
        
        return merged_segments
    
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
    
    def _create_audio_chunks(self, silence_segments: List[Tuple[float, float]], 
                           total_duration: float, progress: ProgressTracker) -> List[Tuple[float, float]]:
        """Stage 3: Create audio chunks between silence gaps"""
        progress.start_stage(3, "Chunk Assembly and Filtering")
        
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
            if total_duration - chunk_start >= self.min_chunk_duration:
                audio_chunks.append((chunk_start, total_duration))
        else:
            # No silence found - treat as single file (no splitting needed)
            print(f"   ℹ️  No silence >= {self.min_silence_duration}s detected - file will be processed as single chunk")
            audio_chunks = [(0.0, total_duration)]
        
        # Filter chunks by minimum duration
        valid_chunks = [(start, end) for start, end in audio_chunks 
                       if end - start >= self.min_chunk_duration]
        
        if len(valid_chunks) > 1:
            print(f"   ✓ Audio will be split into {len(valid_chunks)} chunks")
            for i, (start, end) in enumerate(valid_chunks, 1):
                print(f"      Chunk {i}: {start/60:.1f}m - {end/60:.1f}m ({(end-start)/60:.1f}m)")
        else:
            print(f"   ✓ Audio processed as single file (no chunking needed)")
        
        return valid_chunks
    
    def _export_chunks(self, input_file: Path, audio_chunks: List[Tuple[float, float]], 
                              output_dir: Path, progress: ProgressTracker, 
                              silence_segments: List[Tuple[float, float]]) -> Tuple[int, str]:
        """Stage 4: Export audio chunks with metadata"""
        progress.start_stage(4, "Enhanced Export with Metadata")
        
        if not audio_chunks:
            print("   ⚠️  No chunks to export")
            return 0, ""
        
        # Prepare processing configuration and stats
        processing_config = {
            "sample_rate": self.sample_rate,
            "chunk_duration": self.chunk_duration,
            "silence_threshold": self.silence_threshold,
            "min_silence_duration": self.min_silence_duration,
            "min_chunk_duration": self.min_chunk_duration,
            "keep_silence": self.keep_silence,
            "output_format": self.output_format,
            "create_metadata": self.create_metadata,
            "preserve_timestamps": self.preserve_timestamps
        }
        
        processing_stats = {
            "total_duration": progress.total_duration,
            "processing_time": time.time() - progress.start_time,
            "memory_peak": progress.memory_monitor.peak_memory,
            "memory_increase": progress.memory_monitor.get_increase(),
            "chunks_processed": progress.total_chunks,
            "silence_segments_found": len(silence_segments)
        }
        
        # Export with metadata
        chunk_count, metadata_report = export_with_metadata(
            input_file, audio_chunks, output_dir, processing_config, 
            processing_stats, silence_segments
        )
        
        print(f"   ✅ Exported {chunk_count} chunks with metadata")
        
        return chunk_count, metadata_report
    
    def _create_cancelled_result(self) -> Dict[str, Any]:
        """Create result for cancelled operation"""
        return {
            "success": False,
            "cancelled": True,
            "chunks_created": 0,
            "total_duration": 0,
            "processing_time": 0,
            "error": "Operation cancelled by user"
        }


def process_audio_files(input_dir: Path, output_dir: Path, 
                               chunk_duration: float = 30.0,
                               silence_threshold: float = 0.01,
                               min_silence_duration: float = 25.0,
                               create_metadata: bool = True,
                               output_format: str = 'wav',
                               move_processed: bool = True) -> None:
    """
    Process all audio files with metadata and output options
    """
    # Stage 1: File Discovery
    print(f"🔍 Scanning directory: {input_dir}")
    audio_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.mp4'}
    
    # Get all files, excluding the processed directory
    all_files = []
    for item in input_dir.iterdir():
        if item.is_file():
            all_files.append(item)
        elif item.is_dir() and item.name != 'processed':
            # Optionally scan subdirectories (excluding processed)
            pass
    
    audio_files = []
    total_size = 0
    
    print(f"   Checking {len(all_files)} files...")
    
    for file_path in all_files:
        if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
            audio_files.append(file_path)
            total_size += file_path.stat().st_size
    
    if not audio_files:
        print(f"   ❌ No audio files found")
        print(f"   📝 Supported formats: {', '.join(sorted(audio_extensions))}")
        return
    
    total_size_mb = total_size / (1024 * 1024)
    print(f"   ✓ Found {len(audio_files)} audio files | Total size: {total_size_mb:.1f}MB")
    
    # Display file list with details
    print(f"\n📚 Files to process:")
    for i, audio_file in enumerate(audio_files, 1):
        size_mb = audio_file.stat().st_size / (1024 * 1024)
        print(f"   {i}. {audio_file.name} ({size_mb:.1f}MB)")
    
    # Initialize processor
    processor = AudioProcessor(
        chunk_duration=chunk_duration,
        silence_threshold=silence_threshold,
        min_silence_duration=min_silence_duration,
        create_metadata=create_metadata,
        output_format=output_format
    )
    
    # Stage 2: Process each file
    print(f"\n🚀 Starting batch processing...")
    print(f"   Output format: {output_format.upper()}")
    print(f"   Metadata generation: {'enabled' if create_metadata else 'disabled'}")
    
    session_stats = {
        "total_files": len(audio_files),
        "processed_files": 0,
        "total_chunks": 0,
        "total_processing_time": 0,
        "total_input_duration": 0,
        "total_output_duration": 0,
        "errors": [],
        "cancelled": False
    }
    
    overall_start = time.time()
    
    # Create processed directory if move_processed is enabled
    processed_dir = input_dir / "processed"
    if move_processed:
        processed_dir.mkdir(exist_ok=True)
        print(f"   📁 Processed files will be moved to: {processed_dir}")
    
    # Process files with overall progress
    with tqdm(audio_files, desc="Overall Progress", unit="file") as file_pbar:
        for file_num, audio_file in enumerate(file_pbar, 1):
            file_pbar.set_description(f"Processing ({file_num}/{len(audio_files)})")
            file_pbar.set_postfix({"current": audio_file.name[:20] + "..." if len(audio_file.name) > 20 else audio_file.name})
            
            result = processor.process_audio_file(audio_file, output_dir)
            
            # Update session statistics
            session_stats["processed_files"] += 1
            session_stats["total_chunks"] += result.get("chunks_created", 0)
            session_stats["total_processing_time"] += result.get("processing_time", 0)
            session_stats["total_input_duration"] += result.get("total_duration", 0)
            session_stats["total_output_duration"] += result.get("filtered_duration", 0)
            
            if not result.get("success", False):
                if result.get("cancelled", False):
                    session_stats["cancelled"] = True
                    print(f"\n⚠️  Processing cancelled by user")
                    break
                else:
                    session_stats["errors"].append({
                        "file": audio_file.name, 
                        "error": result.get("error", "Unknown error")
                    })
            else:
                # Move successfully processed file if enabled
                if move_processed:
                    try:
                        dest_path = processed_dir / audio_file.name
                        shutil.move(str(audio_file), str(dest_path))
                        file_pbar.write(f"   ✅ Moved {audio_file.name} to processed/")
                    except Exception as e:
                        file_pbar.write(f"   ⚠️  Failed to move {audio_file.name}: {e}")
    
    # Stage 3: Final Summary
    total_session_time = time.time() - overall_start
    
    print(f"\n🏁 Processing Complete!")
    print(f"="*60)
    print(f"📊 Session Summary:")
    print(f"   Files processed: {session_stats['processed_files']}/{session_stats['total_files']}")
    print(f"   Total chunks created: {session_stats['total_chunks']}")
    print(f"   Input audio duration: {session_stats['total_input_duration']/60:.1f} minutes")
    print(f"   Output audio duration: {session_stats['total_output_duration']/60:.1f} minutes")
    print(f"   Processing time: {session_stats['total_processing_time']:.1f}s")
    print(f"   Total session time: {total_session_time:.1f}s")
    
    if session_stats['total_processing_time'] > 0:
        print(f"   Average speed: {session_stats['total_input_duration']/session_stats['total_processing_time']:.1f}x realtime")
    
    if create_metadata:
        print(f"   📄 Metadata files generated for each processed file")
    
    if session_stats['errors']:
        print(f"\n⚠️  Errors encountered:")
        for error in session_stats['errors']:
            print(f"   - {error['file']}: {error['error']}")
    
    if session_stats['cancelled']:
        print(f"\n⚠️  Session was cancelled by user")
    
    print(f"\n📂 Output saved to: {output_dir}")


def main():
    """Main function for audio splitter"""
    print(f"🎧 Audio Splitter - Metadata Edition")
    print(f"="*60)
    print(f"✨ Features: Real-time progress • Metadata generation • Multiple formats")
    print(f"🔧 Engine: Librosa with output capabilities")
    
    script_dir = Path(__file__).parent
    input_dir = script_dir / "input"
    output_dir = script_dir / "output"
    
    # Check if input directory exists
    if not input_dir.exists():
        print(f"📁 Input directory {input_dir} does not exist. Creating it...")
        input_dir.mkdir(parents=True, exist_ok=True)
        print(f"   ✓ Created directory: {input_dir}")
        print(f"\n📝 Please place your audio files in the 'input' directory and run again.")
        print(f"   Supported formats: MP3, WAV, M4A, FLAC, OGG, AAC, MP4")
        return
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process all audio files with full features
    process_audio_files(
        input_dir, 
        output_dir,
        create_metadata=True,
        output_format='flac'
    )


if __name__ == "__main__":
    main()

