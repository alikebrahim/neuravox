"""Unit tests for shared metadata module"""
import json
import tempfile
from pathlib import Path
from datetime import datetime
import pytest

from neuravox.shared.metadata import ChunkMetadata, ProcessingMetadata, TranscriptionMetadata, MetadataManager


class TestChunkMetadata:
    """Test ChunkMetadata functionality"""
    
    def test_creation(self):
        """Test creating chunk metadata"""
        chunk = ChunkMetadata(
            chunk_index=0,
            total_chunks=5,
            start_time=0.0,
            end_time=30.0,
            duration=30.0,
            file_path=Path("/test/chunk_000.flac"),
            source_file=Path("/test/source.mp3")
        )
        
        assert chunk.chunk_index == 0
        assert chunk.total_chunks == 5
        assert chunk.start_time == 0.0
        assert chunk.end_time == 30.0
        assert chunk.duration == 30.0
        assert chunk.file_path == Path("/test/chunk_000.flac")
        assert chunk.source_file == Path("/test/source.mp3")
    
    def test_to_dict(self):
        """Test converting chunk metadata to dictionary"""
        chunk = ChunkMetadata(
            chunk_index=1,
            total_chunks=3,
            start_time=30.0,
            end_time=60.0,
            duration=30.0,
            file_path=Path("/test/chunk_001.flac"),
            source_file=Path("/test/source.mp3")
        )
        
        chunk_dict = chunk.to_dict()
        
        assert chunk_dict["chunk_index"] == 1
        assert chunk_dict["total_chunks"] == 3
        assert chunk_dict["start_time"] == 30.0
        assert chunk_dict["end_time"] == 60.0
        assert chunk_dict["duration"] == 30.0
        assert chunk_dict["file_path"] == "/test/chunk_001.flac"
        assert chunk_dict["source_file"] == "/test/source.mp3"
    
    def test_duration_calculation(self):
        """Test that duration matches end_time - start_time"""
        chunk = ChunkMetadata(
            chunk_index=0,
            total_chunks=1,
            start_time=10.5,
            end_time=45.7,
            duration=35.2,
            file_path=Path("/test/chunk.flac"),
            source_file=Path("/test/source.mp3")
        )
        
        assert chunk.duration == pytest.approx(chunk.end_time - chunk.start_time, rel=1e-6)


class TestProcessingMetadata:
    """Test ProcessingMetadata functionality"""
    
    def test_creation(self):
        """Test creating processing metadata"""
        chunks = [
            ChunkMetadata(
                chunk_index=0,
                total_chunks=2,
                start_time=0.0,
                end_time=30.0,
                duration=30.0,
                file_path=Path("/test/chunk_000.flac"),
                source_file=Path("/test/source.mp3")
            ),
            ChunkMetadata(
                chunk_index=1,
                total_chunks=2,
                start_time=30.0,
                end_time=60.0,
                duration=30.0,
                file_path=Path("/test/chunk_001.flac"),
                source_file=Path("/test/source.mp3")
            )
        ]
        
        metadata = ProcessingMetadata(
            file_id="test_file_id",
            original_file=Path("/test/source.mp3"),
            processed_at=datetime.now(),
            processing_time=5.5,
            chunks=chunks,
            audio_info={"duration": 60.0, "sample_rate": 44100},
            processing_params={"silence_threshold": 0.01}
        )
        
        assert metadata.file_id == "test_file_id"
        assert metadata.original_file == Path("/test/source.mp3")
        assert metadata.processing_time == 5.5
        assert len(metadata.chunks) == 2
        assert metadata.audio_info["duration"] == 60.0
        assert metadata.processing_params["silence_threshold"] == 0.01
    
    def test_to_dict(self):
        """Test converting processing metadata to dictionary"""
        chunks = [
            ChunkMetadata(
                chunk_index=0,
                total_chunks=1,
                start_time=0.0,
                end_time=30.0,
                duration=30.0,
                file_path=Path("/test/chunk_000.flac"),
                source_file=Path("/test/source.mp3")
            )
        ]
        
        now = datetime.now()
        metadata = ProcessingMetadata(
            file_id="test_id",
            original_file=Path("/test/source.mp3"),
            processed_at=now,
            processing_time=3.5,
            chunks=chunks,
            audio_info={"duration": 30.0},
            processing_params={"output_format": "flac"}
        )
        
        meta_dict = metadata.to_dict()
        
        assert meta_dict["file_id"] == "test_id"
        assert meta_dict["original_file"] == "/test/source.mp3"
        assert meta_dict["processed_at"] == now.isoformat()
        assert meta_dict["processing_time"] == 3.5
        assert len(meta_dict["chunks"]) == 1
        assert meta_dict["chunks"][0]["chunk_index"] == 0
        assert meta_dict["chunks"][0]["file_path"] == "/test/chunk_000.flac"
    
    def test_save_and_load(self):
        """Test saving and loading processing metadata"""
        chunks = [
            ChunkMetadata(
                chunk_index=0,
                total_chunks=1,
                start_time=0.0,
                end_time=30.0,
                duration=30.0,
                file_path=Path("/test/chunk_000.flac"),
                source_file=Path("/test/source.mp3")
            )
        ]
        
        original_metadata = ProcessingMetadata(
            file_id="test_save_load",
            original_file=Path("/test/source.mp3"),
            processed_at=datetime.now(),
            processing_time=2.5,
            chunks=chunks,
            audio_info={"duration": 30.0, "sample_rate": 16000},
            processing_params={"silence_threshold": 0.01}
        )
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            original_metadata.save(temp_path)
            
            # Load from file
            loaded_metadata = ProcessingMetadata.load(temp_path)
            
            # Verify loaded data matches original
            assert loaded_metadata.file_id == original_metadata.file_id
            assert loaded_metadata.original_file == original_metadata.original_file
            assert loaded_metadata.processing_time == original_metadata.processing_time
            assert len(loaded_metadata.chunks) == len(original_metadata.chunks)
            assert loaded_metadata.chunks[0].chunk_index == 0
            assert loaded_metadata.chunks[0].file_path == Path("/test/chunk_000.flac")
            assert loaded_metadata.audio_info == original_metadata.audio_info
            assert loaded_metadata.processing_params == original_metadata.processing_params
        finally:
            temp_path.unlink()


class TestTranscriptionMetadata:
    """Test TranscriptionMetadata functionality"""
    
    def test_creation(self):
        """Test creating transcription metadata"""
        metadata = TranscriptionMetadata(
            file_id="test_transcript",
            model_used="google-gemini",
            transcribed_at=datetime.now(),
            transcription_time=45.5,
            word_count=500,
            char_count=2500,
            chunks_transcribed=5,
            combined=True
        )
        
        assert metadata.file_id == "test_transcript"
        assert metadata.model_used == "google-gemini"
        assert metadata.transcription_time == 45.5
        assert metadata.word_count == 500
        assert metadata.char_count == 2500
        assert metadata.chunks_transcribed == 5
        assert metadata.combined is True
    
    def test_to_dict(self):
        """Test converting transcription metadata to dictionary"""
        now = datetime.now()
        metadata = TranscriptionMetadata(
            file_id="test_dict",
            model_used="openai-whisper",
            transcribed_at=now,
            transcription_time=30.0,
            word_count=300,
            char_count=1500,
            chunks_transcribed=3,
            combined=False
        )
        
        meta_dict = metadata.to_dict()
        
        assert meta_dict["file_id"] == "test_dict"
        assert meta_dict["model_used"] == "openai-whisper"
        assert meta_dict["transcribed_at"] == now.isoformat()
        assert meta_dict["transcription_time"] == 30.0
        assert meta_dict["word_count"] == 300
        assert meta_dict["char_count"] == 1500
        assert meta_dict["chunks_transcribed"] == 3
        assert meta_dict["combined"] is False


class TestMetadataManager:
    """Test MetadataManager functionality"""
    
    def test_create_manifest(self):
        """Test creating a manifest from processing metadata"""
        chunks = [
            ChunkMetadata(
                chunk_index=0,
                total_chunks=2,
                start_time=0.0,
                end_time=30.0,
                duration=30.0,
                file_path=Path("/output/chunk_000.flac"),
                source_file=Path("/input/source.mp3")
            ),
            ChunkMetadata(
                chunk_index=1,
                total_chunks=2,
                start_time=30.0,
                end_time=60.0,
                duration=30.0,
                file_path=Path("/output/chunk_001.flac"),
                source_file=Path("/input/source.mp3")
            )
        ]
        
        processing_metadata = ProcessingMetadata(
            file_id="test_manifest",
            original_file=Path("/input/source.mp3"),
            processed_at=datetime.now(),
            processing_time=5.0,
            chunks=chunks,
            audio_info={"duration": 60.0, "sample_rate": 16000},
            processing_params={"output_format": "flac"}
        )
        
        # Create temporary output directory
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Create manifest
            manifest_path = MetadataManager.create_manifest(processing_metadata, output_dir)
            
            # Verify manifest was created
            assert manifest_path.exists()
            assert manifest_path.name == "test_manifest_manifest.json"
            
            # Load and verify manifest content
            with open(manifest_path) as f:
                manifest = json.load(f)
            
            assert manifest["file_id"] == "test_manifest"
            assert manifest["original_file"] == "/input/source.mp3"
            assert manifest["total_chunks"] == 2
            assert len(manifest["chunks"]) == 2
            assert manifest["chunks"][0]["chunk_index"] == 0
            assert manifest["chunks"][1]["chunk_index"] == 1
            assert manifest["audio_info"]["duration"] == 60.0
    
    def test_load_manifest(self):
        """Test loading a manifest file"""
        # Create test manifest
        manifest_data = {
            "file_id": "test_load",
            "original_file": "/test/audio.mp3",
            "total_chunks": 3,
            "audio_info": {"duration": 90.0, "sample_rate": 22050},
            "chunks": [
                {
                    "chunk_index": 0,
                    "start_time": 0.0,
                    "end_time": 30.0,
                    "file_path": "/test/chunk_000.flac"
                }
            ]
        }
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(manifest_data, f)
            temp_path = Path(f.name)
        
        try:
            # Load manifest
            loaded_manifest = MetadataManager.load_manifest(temp_path)
            
            # Verify loaded data
            assert loaded_manifest["file_id"] == "test_load"
            assert loaded_manifest["original_file"] == "/test/audio.mp3"
            assert loaded_manifest["total_chunks"] == 3
            assert loaded_manifest["audio_info"]["duration"] == 90.0
            assert len(loaded_manifest["chunks"]) == 1
            assert loaded_manifest["chunks"][0]["chunk_index"] == 0
        finally:
            temp_path.unlink()
    
    def test_manifest_with_empty_chunks(self):
        """Test creating manifest with no chunks (single file processing)"""
        processing_metadata = ProcessingMetadata(
            file_id="no_chunks",
            original_file=Path("/input/short.mp3"),
            processed_at=datetime.now(),
            processing_time=1.0,
            chunks=[],  # No chunks - file processed as single unit
            audio_info={"duration": 10.0},
            processing_params={}
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Create manifest
            manifest_path = MetadataManager.create_manifest(processing_metadata, output_dir)
            
            # Load and verify
            manifest = MetadataManager.load_manifest(manifest_path)
            assert manifest["total_chunks"] == 0
            assert manifest["chunks"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])