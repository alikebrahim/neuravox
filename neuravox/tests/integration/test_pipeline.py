"""Integration tests for the full audio processing pipeline"""
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
import numpy as np
import soundfile as sf

from core.pipeline import AudioPipeline
from modules.shared.config import UnifiedConfig
from core.exceptions import PipelineError


class TestAudioPipeline:
    """Test full pipeline integration"""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "input").mkdir()
            (workspace / "processed").mkdir()
            (workspace / "transcribed").mkdir()
            yield workspace
    
    @pytest.fixture
    def test_audio_file(self, temp_workspace):
        """Create a test audio file"""
        # Generate test audio: 10 seconds at 16kHz
        duration = 10  # seconds
        sample_rate = 16000
        t = np.linspace(0, duration, duration * sample_rate)
        
        # Create audio with silence gaps
        audio = np.zeros_like(t)
        
        # Add sound from 0-2 seconds (440Hz tone)
        audio[0:2*sample_rate] = 0.3 * np.sin(2 * np.pi * 440 * t[0:2*sample_rate])
        
        # Silence from 2-5 seconds
        
        # Add sound from 5-7 seconds (880Hz tone)
        audio[5*sample_rate:7*sample_rate] = 0.3 * np.sin(2 * np.pi * 880 * t[5*sample_rate:7*sample_rate])
        
        # Silence from 7-10 seconds
        
        # Save test file
        test_file = temp_workspace / "input" / "test_audio.wav"
        sf.write(str(test_file), audio, sample_rate)
        
        return test_file
    
    @pytest.fixture
    def mock_config(self, temp_workspace):
        """Create mock configuration"""
        config = UnifiedConfig()
        config.workspace.base_path = temp_workspace
        config.processing.min_silence_duration = 2.0  # Shorter for testing
        config.transcription.default_model = "test-model"
        return config
    
    @pytest.mark.asyncio
    async def test_process_single_file(self, test_audio_file, mock_config):
        """Test processing a single audio file through pipeline"""
        pipeline = AudioPipeline(config=mock_config)
        
        # Mock the transcriber to avoid API calls
        mock_transcriber = AsyncMock()
        mock_transcriber.transcribe_chunks = AsyncMock(return_value={
            "success": True,
            "transcription": "Test transcription",
            "chunks": [
                {"chunk_index": 0, "text": "Chunk 1 text"},
                {"chunk_index": 1, "text": "Chunk 2 text"}
            ]
        })
        pipeline.transcriber = mock_transcriber
        
        # Process file
        result = await pipeline.process_file(test_audio_file, model="test-model")
        
        # Verify result structure
        assert result["status"] == "completed"
        assert result["file_id"] is not None
        assert "processing_metadata" in result
        assert "transcription_result" in result
        
        # Verify processing metadata
        metadata = result["processing_metadata"]
        assert metadata["original_file"] == str(test_audio_file)
        assert len(metadata["chunks"]) > 0  # Should have detected chunks
        
        # Verify files were created
        processed_dir = mock_config.workspace.processed_path / result["file_id"]
        assert processed_dir.exists()
        
        # Verify chunk files exist
        chunk_files = list(processed_dir.glob("chunk_*.flac"))
        assert len(chunk_files) == len(metadata["chunks"])
        
        # Verify transcriber was called
        mock_transcriber.transcribe_chunks.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_file_already_processing(self, test_audio_file, mock_config):
        """Test handling file that's already being processed"""
        pipeline = AudioPipeline(config=mock_config)
        
        # Mock state manager to simulate file already processing
        file_id = test_audio_file.stem + "_" + "12345678"
        pipeline.state_manager.get_file_status = MagicMock(
            return_value={"status": "processing"}
        )
        pipeline.audio_processor.process_file = MagicMock(
            return_value=MagicMock(file_id=file_id)
        )
        
        # Should raise error
        with pytest.raises(PipelineError, match="already being processed"):
            await pipeline.process_file(test_audio_file)
    
    @pytest.mark.asyncio
    async def test_process_batch(self, temp_workspace, mock_config):
        """Test processing multiple files"""
        # Create multiple test files
        test_files = []
        for i in range(3):
            audio_file = temp_workspace / "input" / f"test_{i}.wav"
            # Create simple audio file
            audio = np.random.randn(16000)  # 1 second of noise
            sf.write(str(audio_file), audio, 16000)
            test_files.append(audio_file)
        
        pipeline = AudioPipeline(config=mock_config)
        
        # Mock transcriber
        mock_transcriber = AsyncMock()
        mock_transcriber.transcribe_chunks = AsyncMock(return_value={
            "success": True,
            "transcription": "Test transcription"
        })
        pipeline.transcriber = mock_transcriber
        
        # Process batch
        results = await pipeline.process_batch(test_files, model="test-model")
        
        # Verify results
        assert len(results) == 3
        for i, result in enumerate(results):
            if result["status"] == "completed":
                assert result["file_id"] is not None
                assert "processing_metadata" in result
    
    @pytest.mark.asyncio
    async def test_process_with_failure(self, test_audio_file, mock_config):
        """Test handling processing failure"""
        pipeline = AudioPipeline(config=mock_config)
        
        # Mock processor to fail
        pipeline.audio_processor.process_file = MagicMock(
            side_effect=Exception("Processing failed")
        )
        
        # Should handle error
        with pytest.raises(PipelineError, match="Processing failed"):
            await pipeline.process_file(test_audio_file)
        
        # Verify state was updated
        pipeline.state_manager.mark_failed.assert_called()
    
    def test_resume_failed(self, mock_config):
        """Test getting failed files for resume"""
        pipeline = AudioPipeline(config=mock_config)
        
        # Mock state manager
        pipeline.state_manager.get_failed_files = MagicMock(
            return_value=[
                {"file_id": "file1", "original_path": "/path/to/file1.mp3"},
                {"file_id": "file2", "original_path": "/path/to/file2.mp3"}
            ]
        )
        
        failed_files = pipeline.resume_failed()
        
        assert len(failed_files) == 2
        assert failed_files[0]["file_id"] == "file1"
    
    def test_get_status(self, mock_config):
        """Test getting pipeline status"""
        pipeline = AudioPipeline(config=mock_config)
        
        # Mock state manager
        pipeline.state_manager.get_pipeline_summary = MagicMock(
            return_value={
                "total_files": 10,
                "completed": 7,
                "failed": 2,
                "processing": 1
            }
        )
        
        status = pipeline.get_status()
        
        assert status["total_files"] == 10
        assert status["completed"] == 7
        assert status["failed"] == 2
        assert status["processing"] == 1
    
    def test_cleanup_workspace(self, mock_config, temp_workspace):
        """Test workspace cleanup"""
        pipeline = AudioPipeline(config=mock_config)
        
        # Create some test files
        processed_dir = mock_config.workspace.processed_path / "test_id"
        processed_dir.mkdir()
        (processed_dir / "chunk_000.flac").touch()
        (processed_dir / "metadata.json").touch()
        
        # Run cleanup
        pipeline.cleanup_workspace(keep_transcribed=False)
        
        # Verify files were removed
        assert not processed_dir.exists()
    
    @pytest.mark.asyncio
    async def test_progress_tracking(self, test_audio_file, mock_config):
        """Test progress tracking during processing"""
        pipeline = AudioPipeline(config=mock_config)
        
        # Track progress updates
        progress_updates = []
        
        # Mock progress tracker
        def mock_add_task(name, desc, total):
            progress_updates.append(("add", name, desc, total))
            return f"task_{name}"
        
        def mock_update_task(name, advance):
            progress_updates.append(("update", name, advance))
        
        def mock_finish_task(name):
            progress_updates.append(("finish", name))
        
        # Mock transcriber
        mock_transcriber = AsyncMock()
        mock_transcriber.transcribe_chunks = AsyncMock(return_value={
            "success": True,
            "transcription": "Test"
        })
        pipeline.transcriber = mock_transcriber
        
        # Process with mocked progress
        with patch('modules.shared.progress.UnifiedProgressTracker') as mock_tracker_class:
            mock_tracker = MagicMock()
            mock_tracker.add_task = MagicMock(side_effect=mock_add_task)
            mock_tracker.update_task = MagicMock(side_effect=mock_update_task)
            mock_tracker.finish_task = MagicMock(side_effect=mock_finish_task)
            mock_tracker.__enter__ = MagicMock(return_value=mock_tracker)
            mock_tracker.__exit__ = MagicMock(return_value=None)
            mock_tracker_class.return_value = mock_tracker
            
            await pipeline.process_file(test_audio_file)
        
        # Verify progress tracking occurred
        assert any("processing" in update[1] for update in progress_updates if update[0] == "add")
        assert any("transcribing" in update[1] for update in progress_updates if update[0] == "add")
        assert any("processing" in update[1] for update in progress_updates if update[0] == "finish")


class TestPipelineWithRealAudio:
    """Test pipeline with more realistic audio scenarios"""
    
    @pytest.fixture
    def long_audio_file(self, temp_workspace):
        """Create a longer test audio file with multiple silence gaps"""
        # 2 minutes of audio at 16kHz
        duration = 120  # seconds
        sample_rate = 16000
        t = np.linspace(0, duration, duration * sample_rate)
        
        audio = np.zeros_like(t)
        
        # Add several speech segments with 25+ second gaps
        segments = [
            (0, 20),      # 20 seconds of "speech"
            (50, 70),     # 20 seconds of "speech" (30s gap)
            (100, 120)    # 20 seconds of "speech" (30s gap)
        ]
        
        for start, end in segments:
            # Simulate speech with varying frequency
            freq = 440 + np.random.randint(-100, 100)
            audio[start*sample_rate:end*sample_rate] = 0.3 * np.sin(2 * np.pi * freq * t[start*sample_rate:end*sample_rate])
        
        # Save test file
        test_file = temp_workspace / "input" / "long_audio.wav"
        sf.write(str(test_file), audio, sample_rate)
        
        return test_file
    
    @pytest.mark.asyncio
    async def test_process_long_file_with_chunks(self, long_audio_file, mock_config):
        """Test processing longer file that should be split into chunks"""
        pipeline = AudioPipeline(config=mock_config)
        
        # Mock transcriber
        mock_transcriber = AsyncMock()
        
        # Mock to return different text for each chunk
        async def mock_transcribe_chunks(metadata, model, output_dir, progress_callback=None):
            chunks = []
            for i, chunk in enumerate(metadata.chunks):
                chunks.append({
                    "chunk_index": i,
                    "text": f"This is transcribed text for chunk {i+1}"
                })
                if progress_callback:
                    progress_callback()
            
            return {
                "success": True,
                "transcription": " ".join(c["text"] for c in chunks),
                "chunks": chunks
            }
        
        mock_transcriber.transcribe_chunks = mock_transcribe_chunks
        pipeline.transcriber = mock_transcriber
        
        # Process file
        result = await pipeline.process_file(long_audio_file)
        
        # Verify chunks were created (should be 3 based on our audio)
        metadata = result["processing_metadata"]
        assert len(metadata["chunks"]) == 3
        
        # Verify chunk timings
        chunks = metadata["chunks"]
        assert chunks[0]["start_time"] == 0.0
        assert chunks[0]["end_time"] < 30.0  # First chunk should end before silence
        assert chunks[1]["start_time"] > 40.0  # Second chunk should start after silence
        assert chunks[2]["start_time"] > 90.0  # Third chunk should start after second silence
    
    @pytest.mark.asyncio
    async def test_process_file_no_silence(self, temp_workspace, mock_config):
        """Test processing file with no silence (should process as single chunk)"""
        # Create continuous audio file
        duration = 30
        sample_rate = 16000
        t = np.linspace(0, duration, duration * sample_rate)
        audio = 0.3 * np.sin(2 * np.pi * 440 * t)  # Continuous tone
        
        test_file = temp_workspace / "input" / "continuous.wav"
        sf.write(str(test_file), audio, sample_rate)
        
        pipeline = AudioPipeline(config=mock_config)
        
        # Mock transcriber
        mock_transcriber = AsyncMock()
        mock_transcriber.transcribe_chunks = AsyncMock(return_value={
            "success": True,
            "transcription": "Continuous audio transcription",
            "chunks": [{"chunk_index": 0, "text": "Continuous audio transcription"}]
        })
        pipeline.transcriber = mock_transcriber
        
        # Process file
        result = await pipeline.process_file(test_file)
        
        # Should have single chunk
        metadata = result["processing_metadata"]
        assert len(metadata["chunks"]) == 1
        assert metadata["chunks"][0]["duration"] == pytest.approx(duration, rel=0.1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])