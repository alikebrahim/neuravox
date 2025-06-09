"""
Unified metadata handling for audio processing and transcription
"""
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime

@dataclass
class ChunkMetadata:
    """Metadata for audio chunks"""
    chunk_index: int
    total_chunks: int
    start_time: float
    end_time: float
    duration: float
    file_path: Path
    source_file: Path
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "file_path": str(self.file_path),
            "source_file": str(self.source_file)
        }

@dataclass
class ProcessingMetadata:
    """Unified processing metadata"""
    file_id: str
    original_file: Path
    processed_at: datetime
    processing_time: float
    chunks: List[ChunkMetadata]
    audio_info: Dict[str, Any]
    processing_params: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['processed_at'] = self.processed_at.isoformat()
        data['original_file'] = str(self.original_file)
        data['chunks'] = [chunk.to_dict() for chunk in self.chunks]
        return data
    
    def save(self, path: Path):
        """Save metadata to JSON file"""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: Path) -> 'ProcessingMetadata':
        """Load metadata from JSON file"""
        with open(path) as f:
            data = json.load(f)
        
        # Convert back to proper types
        data['processed_at'] = datetime.fromisoformat(data['processed_at'])
        data['original_file'] = Path(data['original_file'])
        data['chunks'] = [
            ChunkMetadata(
                chunk_index=chunk['chunk_index'],
                total_chunks=chunk['total_chunks'],
                start_time=chunk['start_time'],
                end_time=chunk['end_time'],
                duration=chunk['duration'],
                file_path=Path(chunk['file_path']),
                source_file=Path(chunk['source_file'])
            )
            for chunk in data['chunks']
        ]
        return cls(**data)

@dataclass 
class TranscriptionMetadata:
    """Metadata for transcription results"""
    file_id: str
    model_used: str
    transcribed_at: datetime
    transcription_time: float
    word_count: int
    char_count: int
    chunks_transcribed: int
    combined: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "file_id": self.file_id,
            "model_used": self.model_used,
            "transcribed_at": self.transcribed_at.isoformat(),
            "transcription_time": self.transcription_time,
            "word_count": self.word_count,
            "char_count": self.char_count,
            "chunks_transcribed": self.chunks_transcribed,
            "combined": self.combined
        }

class MetadataManager:
    """Central metadata management"""
    
    @staticmethod
    def create_manifest(
        processing_metadata: ProcessingMetadata,
        output_dir: Path
    ) -> Path:
        """Create a manifest file for chunk processing"""
        manifest = {
            "file_id": processing_metadata.file_id,
            "original_file": str(processing_metadata.original_file),
            "total_chunks": len(processing_metadata.chunks),
            "audio_info": processing_metadata.audio_info,
            "chunks": [chunk.to_dict() for chunk in processing_metadata.chunks]
        }
        
        manifest_path = output_dir / f"{processing_metadata.file_id}_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return manifest_path
    
    @staticmethod
    def load_manifest(manifest_path: Path) -> Dict[str, Any]:
        """Load manifest file"""
        with open(manifest_path) as f:
            return json.load(f)