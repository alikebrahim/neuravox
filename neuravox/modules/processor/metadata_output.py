#!/usr/bin/env python3

"""
Metadata and Output Module
Generates detailed metadata, analysis reports, and supports multiple output formats
"""

import json
import csv
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime
import librosa
import soundfile as sf
import numpy as np


class AudioMetadata:
    """Generate and manage audio processing metadata"""
    
    def __init__(self, source_file: Path, processing_config: Dict[str, Any]):
        self.source_file = source_file
        self.processing_config = processing_config
        self.processing_start = datetime.now()
        self.processing_end = None
        self.silence_segments = []
        self.audio_chunks = []
        self.processing_stats = {}
        
    def add_silence_segment(self, start: float, end: float, confidence: float = 1.0):
        """Add a detected silence segment"""
        self.silence_segments.append({
            "start_time": start,
            "end_time": end,
            "duration": end - start,
            "confidence": confidence,
            "start_formatted": self._format_time(start),
            "end_formatted": self._format_time(end),
            "duration_formatted": self._format_duration(end - start)
        })
    
    def add_audio_chunk(self, chunk_id: int, start: float, end: float, output_file: Path):
        """Add an audio chunk to metadata"""
        self.audio_chunks.append({
            "chunk_id": chunk_id,
            "start_time": start,
            "end_time": end,
            "duration": end - start,
            "start_formatted": self._format_time(start),
            "end_formatted": self._format_time(end),
            "duration_formatted": self._format_duration(end - start),
            "output_file": str(output_file.name),
            "file_size_mb": output_file.stat().st_size / (1024 * 1024) if output_file.exists() else 0
        })
    
    def set_processing_stats(self, stats: Dict[str, Any]):
        """Set processing statistics"""
        self.processing_stats = stats
        self.processing_end = datetime.now()
    
    def _format_time(self, seconds: float) -> str:
        """Format time in MM:SS.mmm format"""
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes:02d}:{secs:06.3f}"
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        else:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.1f}s"
    
    def generate_metadata(self) -> Dict[str, Any]:
        """Generate complete metadata dictionary"""
        total_duration = self.processing_stats.get("total_duration", 0)
        processing_time = (self.processing_end - self.processing_start).total_seconds()
        
        metadata = {
            "source_file": {
                "name": self.source_file.name,
                "path": str(self.source_file),
                "size_mb": self.source_file.stat().st_size / (1024 * 1024),
                "duration_seconds": total_duration,
                "duration_formatted": self._format_duration(total_duration)
            },
            "processing": {
                "start_time": self.processing_start.isoformat(),
                "end_time": self.processing_end.isoformat() if self.processing_end else None,
                "processing_time_seconds": processing_time,
                "processing_speed_realtime": total_duration / processing_time if processing_time > 0 else 0,
                "config": self.processing_config,
                "stats": self.processing_stats
            },
            "silence_analysis": {
                "total_silence_segments": len(self.silence_segments),
                "total_silence_duration": sum(seg["duration"] for seg in self.silence_segments),
                "silence_percentage": (sum(seg["duration"] for seg in self.silence_segments) / total_duration * 100) if total_duration > 0 else 0,
                "segments": self.silence_segments
            },
            "output_chunks": {
                "total_chunks": len(self.audio_chunks),
                "total_output_duration": sum(chunk["duration"] for chunk in self.audio_chunks),
                "output_percentage": (sum(chunk["duration"] for chunk in self.audio_chunks) / total_duration * 100) if total_duration > 0 else 0,
                "chunks": self.audio_chunks
            },
            "summary": {
                "input_duration": self._format_duration(total_duration),
                "output_duration": self._format_duration(sum(chunk["duration"] for chunk in self.audio_chunks)),
                "silence_removed": self._format_duration(sum(seg["duration"] for seg in self.silence_segments)),
                "compression_ratio": (sum(chunk["duration"] for chunk in self.audio_chunks) / total_duration) if total_duration > 0 else 0,
                "processing_speed": f"{total_duration / processing_time:.1f}x realtime" if processing_time > 0 else "N/A"
            }
        }
        
        return metadata
    
    def save_json(self, output_file: Path):
        """Save metadata as JSON"""
        metadata = self.generate_metadata()
        with open(output_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def save_csv(self, output_file: Path):
        """Save chunk information as CSV"""
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                "Chunk ID", "Start Time", "End Time", "Duration (s)", 
                "Start (MM:SS)", "End (MM:SS)", "Duration", "Output File", "Size (MB)"
            ])
            
            # Write chunk data
            for chunk in self.audio_chunks:
                writer.writerow([
                    chunk["chunk_id"],
                    f"{chunk['start_time']:.3f}",
                    f"{chunk['end_time']:.3f}",
                    f"{chunk['duration']:.3f}",
                    chunk["start_formatted"],
                    chunk["end_formatted"],
                    chunk["duration_formatted"],
                    chunk["output_file"],
                    f"{chunk['file_size_mb']:.2f}"
                ])
    
    def generate_report(self) -> str:
        """Generate human-readable processing report"""
        metadata = self.generate_metadata()
        
        report = []
        report.append("🎧 Audio Processing Report")
        report.append("=" * 50)
        
        # Source file info
        source = metadata["source_file"]
        report.append(f"\n📁 Source File:")
        report.append(f"   Name: {source['name']}")
        report.append(f"   Size: {source['size_mb']:.1f}MB")
        report.append(f"   Duration: {source['duration_formatted']}")
        
        # Processing info
        processing = metadata["processing"]
        report.append(f"\n⚙️  Processing:")
        report.append(f"   Start: {processing['start_time']}")
        report.append(f"   Duration: {processing['processing_time_seconds']:.2f}s")
        report.append(f"   Speed: {processing['processing_speed_realtime']:.1f}x realtime")
        
        # Silence analysis
        silence = metadata["silence_analysis"]
        report.append(f"\n🔇 Silence Analysis:")
        report.append(f"   Segments found: {silence['total_silence_segments']}")
        report.append(f"   Total silence: {self._format_duration(silence['total_silence_duration'])}")
        report.append(f"   Silence percentage: {silence['silence_percentage']:.1f}%")
        
        if silence["segments"]:
            report.append(f"   Silence segments:")
            for i, seg in enumerate(silence["segments"], 1):
                report.append(f"      {i}. {seg['start_formatted']} - {seg['end_formatted']} ({seg['duration_formatted']})")
        
        # Output chunks
        output = metadata["output_chunks"]
        report.append(f"\n📊 Output Chunks:")
        report.append(f"   Total chunks: {output['total_chunks']}")
        report.append(f"   Output duration: {self._format_duration(output['total_output_duration'])}")
        report.append(f"   Retention: {output['output_percentage']:.1f}%")
        
        if output["chunks"]:
            report.append(f"   Chunk details:")
            for chunk in output["chunks"]:
                report.append(f"      {chunk['chunk_id']}. {chunk['start_formatted']} - {chunk['end_formatted']} "
                            f"({chunk['duration_formatted']}) → {chunk['output_file']}")
        
        # Summary
        summary = metadata["summary"]
        report.append(f"\n📈 Summary:")
        report.append(f"   Input: {summary['input_duration']}")
        report.append(f"   Output: {summary['output_duration']}")
        report.append(f"   Removed: {summary['silence_removed']}")
        report.append(f"   Compression: {summary['compression_ratio']:.1%}")
        report.append(f"   Speed: {summary['processing_speed']}")
        
        return "\n".join(report)


class MultiFormatExporter:
    """Export audio chunks in multiple formats"""
    
    SUPPORTED_FORMATS = {
        'wav': {'ext': '.wav', 'subtype': 'PCM_16'},
        'flac': {'ext': '.flac', 'requires_ffmpeg': True, 'optimized': True},
        'mp3': {'ext': '.mp3', 'requires_ffmpeg': True}
    }
    
    def __init__(self, sample_rate: int = 22050, target_sample_rate: int = 16000, 
                 flac_compression_level: int = 8):
        self.sample_rate = sample_rate
        self.target_sample_rate = target_sample_rate
        self.flac_compression_level = flac_compression_level
    
    def export_chunk(self, audio_data: np.ndarray, output_file: Path, 
                    format_type: str = 'wav', quality: str = 'high') -> bool:
        """Export audio chunk in specified format"""
        try:
            if format_type not in self.SUPPORTED_FORMATS:
                raise ValueError(f"Unsupported format: {format_type}")
            
            format_info = self.SUPPORTED_FORMATS[format_type]
            
            if format_type == 'mp3':
                return self._export_mp3(audio_data, output_file, quality)
            elif format_type == 'flac' and format_info.get('optimized', False):
                return self._export_flac_optimized(audio_data, output_file)
            else:
                # Use soundfile for WAV and legacy FLAC
                sf.write(str(output_file), audio_data, self.sample_rate, 
                        subtype=format_info['subtype'])
                return True
                
        except Exception as e:
            print(f"⚠️  Error exporting {output_file}: {e}")
            return False
    
    def _export_flac_optimized(self, audio_data: np.ndarray, output_file: Path) -> bool:
        """Export as optimized FLAC using FFmpeg (16kHz, 16-bit, mono)"""
        try:
            import subprocess
            import tempfile
            
            # First save as temporary WAV at original sample rate
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                sf.write(temp_wav.name, audio_data, self.sample_rate)
                
                # Convert to optimized FLAC using FFmpeg
                cmd = [
                    'ffmpeg', 
                    '-i', temp_wav.name,
                    '-ar', str(self.target_sample_rate),  # Resample to 16kHz
                    '-ac', '1',                           # Convert to mono
                    '-c:a', 'flac',                       # Use FLAC codec
                    '-compression_level', str(self.flac_compression_level),  # Compression level 8
                    '-sample_fmt', 's16',                 # 16-bit sample format
                    '-y',                                 # Overwrite output file
                    str(output_file)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                # Clean up temp file
                Path(temp_wav.name).unlink()
                
                if result.returncode != 0:
                    print(f"⚠️  FFmpeg FLAC conversion failed: {result.stderr}")
                    return False
                
                return True
                
        except Exception as e:
            print(f"⚠️  Optimized FLAC export failed: {e}")
            return False
    
    def export_full_file_flac(self, input_file: Path, output_file: Path) -> bool:
        """Export full audio file as optimized FLAC directly using FFmpeg"""
        try:
            import subprocess
            
            # Convert full file to optimized FLAC using FFmpeg
            cmd = [
                'ffmpeg', 
                '-i', str(input_file),
                '-ar', str(self.target_sample_rate),  # Resample to 16kHz
                '-ac', '1',                           # Convert to mono
                '-c:a', 'flac',                       # Use FLAC codec
                '-compression_level', str(self.flac_compression_level),  # Compression level 8
                '-sample_fmt', 's16',                 # 16-bit sample format
                '-y',                                 # Overwrite output file
                str(output_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"⚠️  FFmpeg full file FLAC conversion failed: {result.stderr}")
                return False
            
            return True
            
        except Exception as e:
            print(f"⚠️  Full file FLAC export failed: {e}")
            return False
    
    def _export_mp3(self, audio_data: np.ndarray, output_file: Path, quality: str) -> bool:
        """Export as MP3 using FFmpeg"""
        try:
            import subprocess
            import tempfile
            
            # First save as temporary WAV
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                sf.write(temp_wav.name, audio_data, self.sample_rate)
                
                # Convert to MP3 using FFmpeg
                quality_map = {
                    'high': '128k',
                    'medium': '96k',
                    'low': '64k'
                }
                bitrate = quality_map.get(quality, '128k')
                
                cmd = [
                    'ffmpeg', '-i', temp_wav.name, '-b:a', bitrate, 
                    '-y', str(output_file)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                # Clean up temp file
                Path(temp_wav.name).unlink()
                
                return result.returncode == 0
                
        except Exception as e:
            print(f"⚠️  MP3 export failed: {e}")
            return False


class OutputManager:
    """Manage output with metadata and multiple formats"""
    
    def __init__(self, output_dir: Path, create_metadata: bool = True, 
                 output_format: str = 'wav', preserve_timestamps: bool = True,
                 target_sample_rate: int = 16000, flac_compression_level: int = 8):
        self.output_dir = output_dir
        self.create_metadata = create_metadata
        self.output_format = output_format
        self.preserve_timestamps = preserve_timestamps
        self.target_sample_rate = target_sample_rate
        self.flac_compression_level = flac_compression_level
        self.exporter = MultiFormatExporter(
            target_sample_rate=target_sample_rate,
            flac_compression_level=flac_compression_level
        )
        
    def create_output_structure(self, source_file: Path) -> Path:
        """Create organized output directory structure"""
        file_output_dir = self.output_dir / source_file.stem
        file_output_dir.mkdir(parents=True, exist_ok=True)
        
        if self.create_metadata:
            # Create metadata subdirectory
            metadata_dir = file_output_dir / "metadata"
            metadata_dir.mkdir(exist_ok=True)
        
        return file_output_dir
    
    def export_chunks_with_metadata(self, source_file: Path, audio_chunks: List[Tuple[float, float]], 
                                   processing_config: Dict[str, Any], 
                                   processing_stats: Dict[str, Any]) -> Tuple[int, AudioMetadata]:
        """Export audio chunks with comprehensive metadata"""
        file_output_dir = self.create_output_structure(source_file)
        metadata = AudioMetadata(source_file, processing_config)
        
        exported_count = 0
        
        # Always export full original file first
        format_ext = MultiFormatExporter.SUPPORTED_FORMATS[self.output_format]['ext']
        full_file_output = file_output_dir / f"{source_file.stem}_full_16k{format_ext}"
        
        print(f"   🎵 Converting full file to optimized {self.output_format.upper()}...")
        if self.output_format == 'flac':
            success = self.exporter.export_full_file_flac(source_file, full_file_output)
        else:
            # For other formats, use the chunk export method but load the whole file
            try:
                y, sr = librosa.load(str(source_file), sr=self.exporter.sample_rate)
                success = self.exporter.export_chunk(y, full_file_output, self.output_format)
            except Exception as e:
                print(f"   ⚠️  Error loading full file: {e}")
                success = False
        
        if success:
            print(f"   ✅ Full file converted: {full_file_output.name}")
            # Add full file to metadata (but don't count it in exported_count)
            total_duration = processing_stats.get("total_duration", 0)
            metadata.add_audio_chunk(0, 0.0, total_duration, full_file_output)
            # Don't increment exported_count for the full file
        else:
            print(f"   ❌ Failed to convert full file")
        
        # Export audio chunks only if there are multiple chunks (actual splitting occurred)
        if audio_chunks and len(audio_chunks) > 1:
            # Create chunks subdirectory
            chunks_dir = file_output_dir / "chunks"
            chunks_dir.mkdir(exist_ok=True)
            
            print(f"   🔪 Converting {len(audio_chunks)} chunks to optimized {self.output_format.upper()}...")
            for i, (start, end) in enumerate(audio_chunks, 1):
                try:
                    # Load audio segment
                    y, sr = librosa.load(str(source_file), sr=self.exporter.sample_rate, 
                                       offset=start, duration=end-start)
                    
                    # Place chunk files in chunks/ subdirectory
                    output_file = chunks_dir / f"{source_file.stem}_chunk{i:02d}_16k{format_ext}"
                    
                    # Export in specified format
                    if self.exporter.export_chunk(y, output_file, self.output_format):
                        exported_count += 1
                        metadata.add_audio_chunk(i, start, end, output_file)
                        
                        # Preserve timestamps if requested
                        if self.preserve_timestamps and output_file.exists():
                            source_mtime = source_file.stat().st_mtime
                            import os
                            os.utime(str(output_file), (source_mtime, source_mtime))
                    
                except Exception as e:
                    print(f"   ⚠️  Error exporting chunk {i}: {e}")
                    continue
            
            print(f"   ✅ Exported {exported_count} chunks successfully")
        else:
            print(f"   ℹ️  No splitting occurred - only full file converted")
        
        # Set processing statistics
        metadata.set_processing_stats(processing_stats)
        
        # Generate metadata files if requested
        if self.create_metadata:
            self._save_metadata_files(file_output_dir, metadata)
        
        # Return actual chunk count (only individual split chunks, not full file)
        return exported_count, metadata
    
    def _save_metadata_files(self, output_dir: Path, metadata: AudioMetadata):
        """Save various metadata files"""
        metadata_dir = output_dir / "metadata"
        
        try:
            # JSON metadata
            metadata.save_json(metadata_dir / "processing_metadata.json")
            
            # CSV chunk list
            metadata.save_csv(metadata_dir / "chunks.csv")
            
            # Human-readable report
            report = metadata.generate_report()
            with open(metadata_dir / "processing_report.txt", 'w') as f:
                f.write(report)
            
            # Processing configuration
            with open(metadata_dir / "config.json", 'w') as f:
                json.dump(metadata.processing_config, f, indent=2)
            
            print(f"   📄 Metadata saved to: {metadata_dir}")
            
        except Exception as e:
            print(f"   ⚠️  Error saving metadata: {e}")


# Integration functions for the main audio processor

def create_output_manager(config: Dict[str, Any]) -> OutputManager:
    """Create output manager from configuration"""
    output_config = config.get("output", {})
    
    return OutputManager(
        output_dir=Path("output"),  # Will be overridden by caller
        create_metadata=output_config.get("create_metadata", True),
        output_format=output_config.get("format", "wav"),
        preserve_timestamps=output_config.get("preserve_timestamps", True)
    )


def export_with_metadata(source_file: Path, audio_chunks: List[Tuple[float, float]], 
                                 output_dir: Path, processing_config: Dict[str, Any], 
                                 processing_stats: Dict[str, Any], 
                                 silence_segments: List[Tuple[float, float]]) -> Tuple[int, str]:
    """Export chunks with metadata and return summary"""
    
    # Create output manager with optimized FLAC settings
    output_manager = OutputManager(
        output_dir=output_dir,
        create_metadata=processing_config.get("create_metadata", True),
        output_format=processing_config.get("output_format", "flac"),
        preserve_timestamps=processing_config.get("preserve_timestamps", True),
        target_sample_rate=16000,
        flac_compression_level=8
    )
    
    # Export chunks with metadata
    exported_count, metadata = output_manager.export_chunks_with_metadata(
        source_file, audio_chunks, processing_config, processing_stats
    )
    
    # Add silence segments to metadata
    for start, end in silence_segments:
        metadata.add_silence_segment(start, end)
    
    # Generate summary report
    summary_report = metadata.generate_report()
    
    return exported_count, summary_report

