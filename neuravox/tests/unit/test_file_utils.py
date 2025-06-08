"""Unit tests for shared file utilities module"""
import os
import tempfile
from pathlib import Path
import pytest

from modules.shared.file_utils import (
    ensure_directory,
    create_file_id,
    get_audio_files,
    format_file_size,
    cleanup_empty_directories,
    move_file_safely,
    calculate_file_hash,
    format_duration,
    load_json_file,
    save_json_file,
    get_relative_path
)


class TestEnsureDirectory:
    """Test ensure_directory functionality"""
    
    def test_create_new_directory(self):
        """Test creating a new directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "test_dir"
            
            # Directory should not exist
            assert not new_dir.exists()
            
            # Create directory
            result = ensure_directory(new_dir)
            
            # Verify directory was created
            assert new_dir.exists()
            assert new_dir.is_dir()
            assert result == new_dir
    
    def test_existing_directory(self):
        """Test with existing directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            existing_dir = Path(temp_dir)
            
            # Directory already exists
            assert existing_dir.exists()
            
            # Should not raise error
            result = ensure_directory(existing_dir)
            
            # Should return the same path
            assert result == existing_dir
            assert existing_dir.exists()
    
    def test_nested_directory_creation(self):
        """Test creating nested directories"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_dir = Path(temp_dir) / "level1" / "level2" / "level3"
            
            # Create nested structure
            result = ensure_directory(nested_dir)
            
            # Verify all levels were created
            assert nested_dir.exists()
            assert nested_dir.is_dir()
            assert (Path(temp_dir) / "level1").exists()
            assert (Path(temp_dir) / "level1" / "level2").exists()
    
    def test_file_path_handling(self):
        """Test handling when path points to a file"""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file_path = Path(temp_file.name)
            
            try:
                # Should handle gracefully or raise appropriate error
                # This depends on implementation
                with pytest.raises(Exception):
                    ensure_directory(file_path)
            finally:
                file_path.unlink()


class TestCreateFileId:
    """Test create_file_id functionality"""
    
    def test_simple_filename(self):
        """Test creating ID from simple filename"""
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"test content")
            
            try:
                file_id = create_file_id(temp_path)
                
                # Should contain stem and hash
                assert temp_path.stem in file_id
                assert '_' in file_id
                parts = file_id.split('_')
                assert len(parts) >= 2
                assert len(parts[-1]) == 8  # 8 character hash
            finally:
                temp_path.unlink()
    
    def test_consistency(self):
        """Test that same file always produces same ID"""
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"consistent content")
            
            try:
                id1 = create_file_id(temp_path)
                id2 = create_file_id(temp_path)
                
                assert id1 == id2
            finally:
                temp_path.unlink()
    
    def test_different_content_different_id(self):
        """Test that different content produces different IDs"""
        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = Path(temp_dir) / "file1.mp3"
            file2 = Path(temp_dir) / "file2.mp3"
            
            file1.write_bytes(b"content 1")
            file2.write_bytes(b"content 2")
            
            id1 = create_file_id(file1)
            id2 = create_file_id(file2)
            
            # Different content should produce different hashes
            assert id1 != id2


class TestGetAudioFiles:
    """Test get_audio_files functionality"""
    
    def test_find_audio_files(self):
        """Test finding audio files in directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            audio_files = [
                "test1.mp3",
                "test2.wav",
                "test3.flac",
                "test4.m4a",
                "test5.ogg"
            ]
            
            for filename in audio_files:
                (temp_path / filename).touch()
            
            # Create non-audio files
            (temp_path / "document.txt").touch()
            (temp_path / "image.png").touch()
            
            # Get audio files
            found_files = get_audio_files(temp_path)
            
            # Should find all audio files
            assert len(found_files) == 5
            found_names = {f.name for f in found_files}
            assert found_names == set(audio_files)
    
    def test_empty_directory(self):
        """Test with empty directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            found_files = get_audio_files(Path(temp_dir))
            assert found_files == []
    
    def test_custom_extensions(self):
        """Test with custom extensions"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create files with custom extensions
            (temp_path / "audio.mp3").touch()
            (temp_path / "audio.custom").touch()
            (temp_path / "audio.xyz").touch()
            
            # Search with custom extensions
            found_files = get_audio_files(temp_path, extensions=['.mp3', '.custom'])
            
            # Should find only specified extensions
            assert len(found_files) == 2
            found_names = {f.name for f in found_files}
            assert found_names == {"audio.mp3", "audio.custom"}
    
    def test_case_insensitive_extensions(self):
        """Test handling of uppercase extensions"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create files with various case extensions
            files = ["test.MP3", "test.Wav", "test.FLAC"]
            for filename in files:
                (temp_path / filename).touch()
            
            found_files = get_audio_files(temp_path)
            assert len(found_files) == 3


class TestFormatFileSize:
    """Test format_file_size functionality"""
    
    def test_bytes(self):
        """Test formatting bytes"""
        assert format_file_size(0) == "0 B"
        assert format_file_size(100) == "100 B"
        assert format_file_size(1023) == "1023 B"
    
    def test_kilobytes(self):
        """Test formatting kilobytes"""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1536) == "1.5 KB"
        assert format_file_size(1024 * 10) == "10.0 KB"
    
    def test_megabytes(self):
        """Test formatting megabytes"""
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 5.5) == "5.5 MB"
        assert format_file_size(1024 * 1024 * 100) == "100.0 MB"
    
    def test_gigabytes(self):
        """Test formatting gigabytes"""
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"
        assert format_file_size(1024 * 1024 * 1024 * 2.5) == "2.5 GB"
    
    def test_terabytes(self):
        """Test formatting terabytes"""
        assert format_file_size(1024 * 1024 * 1024 * 1024) == "1.0 TB"
    
    def test_precision(self):
        """Test decimal precision"""
        # Should show one decimal place
        assert format_file_size(1024 * 1.234) == "1.2 KB"
        assert format_file_size(1024 * 1024 * 1.567) == "1.6 MB"
    
    def test_negative_sizes(self):
        """Test handling negative sizes"""
        # Should handle gracefully
        assert format_file_size(-100) == "-100 B"
        assert format_file_size(-1024) == "-1.0 KB"


class TestCleanupEmptyDirectories:
    """Test cleanup_empty_directories functionality"""
    
    def test_cleanup_empty_dirs(self):
        """Test removing empty directories"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create empty directories
            (temp_path / "empty1").mkdir()
            (temp_path / "empty2" / "nested_empty").mkdir(parents=True)
            
            # Create directory with file
            (temp_path / "not_empty").mkdir()
            (temp_path / "not_empty" / "file.txt").touch()
            
            # Run cleanup
            cleanup_empty_directories(temp_path)
            
            # Empty directories should be removed
            assert not (temp_path / "empty1").exists()
            assert not (temp_path / "empty2").exists()
            
            # Non-empty directory should remain
            assert (temp_path / "not_empty").exists()
            assert (temp_path / "not_empty" / "file.txt").exists()
    
    def test_preserve_root(self):
        """Test that root directory is preserved"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Run cleanup on empty root
            cleanup_empty_directories(temp_path)
            
            # Root should still exist
            assert temp_path.exists()
    
    def test_nested_empty_cleanup(self):
        """Test cleaning nested empty directories"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create nested structure
            nested = temp_path / "a" / "b" / "c" / "d"
            nested.mkdir(parents=True)
            
            # Add file in middle
            (temp_path / "a" / "b" / "file.txt").touch()
            
            # Run cleanup
            cleanup_empty_directories(temp_path)
            
            # Directories with file and above should exist
            assert (temp_path / "a").exists()
            assert (temp_path / "a" / "b").exists()
            assert (temp_path / "a" / "b" / "file.txt").exists()
            
            # Empty nested directories should be removed
            assert not (temp_path / "a" / "b" / "c").exists()


class TestMoveFileSafely:
    """Test move_file_safely functionality"""
    
    def test_simple_move(self):
        """Test moving file to new location"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create source file
            source = temp_path / "source.txt"
            source.write_text("test content")
            
            # Define destination
            dest = temp_path / "dest.txt"
            
            # Move file
            result = move_file_safely(source, dest)
            
            # Verify move
            assert not source.exists()
            assert dest.exists()
            assert dest.read_text() == "test content"
            assert result == dest
    
    def test_move_to_existing_file(self):
        """Test moving to location with existing file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create source and destination files
            source = temp_path / "source.txt"
            source.write_text("source content")
            
            dest = temp_path / "dest.txt"
            dest.write_text("existing content")
            
            # Should rename to avoid overwriting
            result = move_file_safely(source, dest)
            
            # Verify renamed file
            assert not source.exists()
            assert dest.exists()  # Original dest still exists
            assert dest.read_text() == "existing content"
            assert result != dest  # New name
            assert result.exists()
            assert result.read_text() == "source content"
            assert "_1" in result.stem  # Should have counter suffix
    
    def test_move_with_multiple_conflicts(self):
        """Test moving with multiple existing files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create source file
            source = temp_path / "source.txt"
            source.write_text("new content")
            
            # Create existing files
            (temp_path / "dest.txt").write_text("existing 1")
            (temp_path / "dest_1.txt").write_text("existing 2")
            (temp_path / "dest_2.txt").write_text("existing 3")
            
            # Move file
            result = move_file_safely(source, temp_path / "dest.txt")
            
            # Should create dest_3.txt
            assert result.name == "dest_3.txt"
            assert result.read_text() == "new content"
    
    def test_move_to_different_directory(self):
        """Test moving file to different directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create source file
            source = temp_path / "source.txt"
            source.write_text("content")
            
            # Create destination directory
            dest_dir = temp_path / "subdir"
            dest_dir.mkdir()
            dest = dest_dir / "moved.txt"
            
            # Move file
            result = move_file_safely(source, dest)
            
            # Verify move
            assert not source.exists()
            assert dest.exists()
            assert dest.read_text() == "content"


class TestCalculateFileHash:
    """Test calculate_file_hash functionality"""
    
    def test_hash_consistency(self):
        """Test that same content produces same hash"""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"test content for hashing")
            
            try:
                hash1 = calculate_file_hash(temp_path)
                hash2 = calculate_file_hash(temp_path)
                
                assert hash1 == hash2
                assert len(hash1) == 64  # SHA256 produces 64 hex chars
            finally:
                temp_path.unlink()
    
    def test_different_content_different_hash(self):
        """Test that different content produces different hashes"""
        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = Path(temp_dir) / "file1.txt"
            file2 = Path(temp_dir) / "file2.txt"
            
            file1.write_bytes(b"content 1")
            file2.write_bytes(b"content 2")
            
            hash1 = calculate_file_hash(file1)
            hash2 = calculate_file_hash(file2)
            
            assert hash1 != hash2
    
    def test_large_file(self):
        """Test hashing large file"""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            # Write 10MB of data
            for _ in range(1024):
                temp_file.write(b"x" * 10240)
            
            try:
                hash_result = calculate_file_hash(temp_path)
                assert len(hash_result) == 64
            finally:
                temp_path.unlink()


class TestFormatDuration:
    """Test format_duration functionality"""
    
    def test_seconds_only(self):
        """Test formatting seconds"""
        assert format_duration(0) == "00:00"
        assert format_duration(30) == "00:30"
        assert format_duration(59) == "00:59"
    
    def test_minutes_and_seconds(self):
        """Test formatting minutes and seconds"""
        assert format_duration(60) == "01:00"
        assert format_duration(90) == "01:30"
        assert format_duration(3599) == "59:59"
    
    def test_hours_minutes_seconds(self):
        """Test formatting with hours"""
        assert format_duration(3600) == "01:00:00"
        assert format_duration(3661) == "01:01:01"
        assert format_duration(7200) == "02:00:00"
        assert format_duration(10800) == "03:00:00"
    
    def test_decimal_seconds(self):
        """Test handling decimal seconds"""
        assert format_duration(30.5) == "00:30"
        assert format_duration(90.9) == "01:30"


class TestLoadJsonFile:
    """Test load_json_file functionality"""
    
    def test_load_valid_json(self):
        """Test loading valid JSON file"""
        test_data = {"key": "value", "number": 123, "list": [1, 2, 3]}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            import json
            json.dump(test_data, f)
            temp_path = Path(f.name)
        
        try:
            loaded_data = load_json_file(temp_path)
            assert loaded_data == test_data
        finally:
            temp_path.unlink()
    
    def test_load_invalid_json(self):
        """Test loading invalid JSON file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content {")
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="Error loading JSON"):
                load_json_file(temp_path)
        finally:
            temp_path.unlink()
    
    def test_load_nonexistent_file(self):
        """Test loading non-existent file"""
        with pytest.raises(ValueError, match="Error loading JSON"):
            load_json_file(Path("/nonexistent/file.json"))


class TestSaveJsonFile:
    """Test save_json_file functionality"""
    
    def test_save_json(self):
        """Test saving JSON data"""
        test_data = {"name": "test", "values": [1, 2, 3], "nested": {"a": 1}}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "output.json"
            
            save_json_file(test_data, output_path)
            
            # Verify file was created and contains correct data
            assert output_path.exists()
            
            import json
            with open(output_path) as f:
                loaded_data = json.load(f)
            
            assert loaded_data == test_data
    
    def test_save_with_parent_creation(self):
        """Test saving JSON with parent directory creation"""
        test_data = {"test": "data"}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "nested" / "dir" / "output.json"
            
            save_json_file(test_data, output_path)
            
            assert output_path.exists()
            assert output_path.parent.exists()
    
    def test_save_with_path_objects(self):
        """Test saving JSON with Path objects (should convert to string)"""
        test_data = {"path": Path("/test/path"), "number": 42}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "output.json"
            
            save_json_file(test_data, output_path)
            
            import json
            with open(output_path) as f:
                loaded_data = json.load(f)
            
            assert loaded_data["path"] == "/test/path"
            assert loaded_data["number"] == 42


class TestGetRelativePath:
    """Test get_relative_path functionality"""
    
    def test_simple_relative_path(self):
        """Test getting simple relative path"""
        base = Path("/home/user/project")
        path = Path("/home/user/project/src/file.py")
        
        result = get_relative_path(path, base)
        assert result == Path("src/file.py")
    
    def test_already_relative(self):
        """Test with already relative path"""
        base = Path("/home/user")
        path = Path("/home/user/file.txt")
        
        result = get_relative_path(path, base)
        assert result == Path("file.txt")
    
    def test_not_relative(self):
        """Test when path is not relative to base"""
        base = Path("/home/user")
        path = Path("/other/location/file.txt")
        
        result = get_relative_path(path, base)
        assert result == path  # Should return original path
    
    def test_same_path(self):
        """Test when path and base are the same"""
        base = Path("/home/user")
        path = Path("/home/user")
        
        result = get_relative_path(path, base)
        assert result == Path(".")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])