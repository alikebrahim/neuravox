"""Unit tests for shared configuration module"""
import os
import tempfile
from pathlib import Path
import pytest
import yaml

from neuravox.shared.config import UnifiedConfig, WorkspaceConfig, ProcessingConfig, TranscriptionConfig, APIKeysConfig


class TestWorkspaceConfig:
    """Test WorkspaceConfig functionality"""
    
    def test_default_values(self):
        """Test default workspace configuration"""
        config = WorkspaceConfig()
        assert config.base_path == Path.home() / "neuravox"
        assert config.input_dir == "input"
        assert config.processed_dir == "processed"
        assert config.transcribed_dir == "transcribed"
    
    def test_custom_values(self):
        """Test custom workspace configuration"""
        custom_path = Path("/custom/path")
        config = WorkspaceConfig(
            base_path=custom_path,
            input_dir="custom_input",
            processed_dir="custom_processed",
            transcribed_dir="custom_transcribed"
        )
        assert config.base_path == custom_path
        assert config.input_dir == "custom_input"
        assert config.processed_dir == "custom_processed"
        assert config.transcribed_dir == "custom_transcribed"
    
    def test_path_properties(self):
        """Test computed path properties"""
        base = Path("/test/base")
        config = WorkspaceConfig(base_path=base)
        assert config.input_path == base / "input"
        assert config.processed_path == base / "processed"
        assert config.transcribed_path == base / "transcribed"


class TestProcessingConfig:
    """Test ProcessingConfig functionality"""
    
    def test_default_values(self):
        """Test default processing configuration"""
        config = ProcessingConfig()
        assert config.silence_threshold == 0.01
        assert config.min_silence_duration == 25.0
        assert config.min_chunk_duration == 5.0
        assert config.output_format == "flac"
        assert config.preserve_timestamps is True
    
    def test_custom_values(self):
        """Test custom processing configuration"""
        config = ProcessingConfig(
            silence_threshold=0.02,
            min_silence_duration=30.0,
            output_format="wav"
        )
        assert config.silence_threshold == 0.02
        assert config.min_silence_duration == 30.0
        assert config.output_format == "wav"


class TestTranscriptionConfig:
    """Test TranscriptionConfig functionality"""
    
    def test_default_values(self):
        """Test default transcription configuration"""
        config = TranscriptionConfig()
        assert config.default_model == "google-gemini"
        assert config.max_concurrent == 3
        assert config.chunk_processing is True
        assert config.include_timestamps is True
    
    def test_custom_values(self):
        """Test custom transcription configuration"""
        config = TranscriptionConfig(
            default_model="openai-whisper",
            max_concurrent=5,
            chunk_processing=False
        )
        assert config.default_model == "openai-whisper"
        assert config.max_concurrent == 5
        assert config.chunk_processing is False


class TestAPIKeysConfig:
    """Test APIKeysConfig functionality"""
    
    def test_default_values(self):
        """Test default API keys configuration"""
        # Clear any existing env vars
        env_vars = ['GOOGLE_API_KEY', 'OPENAI_API_KEY']
        original_values = {}
        for var in env_vars:
            original_values[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]
        
        try:
            config = APIKeysConfig()
            assert config.google_api_key is None
            assert config.openai_api_key is None
        finally:
            # Restore original values
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
    
    def test_env_var_loading(self):
        """Test loading API keys from environment variables"""
        # Set test env vars
        test_google_key = "test_google_key_123"
        test_openai_key = "test_openai_key_456"
        
        os.environ['GOOGLE_API_KEY'] = test_google_key
        os.environ['OPENAI_API_KEY'] = test_openai_key
        
        try:
            config = APIKeysConfig()
            assert config.google_api_key == test_google_key
            assert config.openai_api_key == test_openai_key
        finally:
            # Clean up
            del os.environ['GOOGLE_API_KEY']
            del os.environ['OPENAI_API_KEY']
    
    def test_direct_values(self):
        """Test setting API keys directly"""
        config = APIKeysConfig(
            google_api_key="direct_google_key",
            openai_api_key="direct_openai_key"
        )
        assert config.google_api_key == "direct_google_key"
        assert config.openai_api_key == "direct_openai_key"


class TestUnifiedConfig:
    """Test UnifiedConfig functionality"""
    
    def test_default_initialization(self):
        """Test default configuration initialization"""
        config = UnifiedConfig()
        
        # Check all sub-configs are initialized
        assert isinstance(config.workspace, WorkspaceConfig)
        assert isinstance(config.processing, ProcessingConfig)
        assert isinstance(config.transcription, TranscriptionConfig)
        assert isinstance(config.api_keys, APIKeysConfig)
    
    def test_load_from_yaml(self):
        """Test loading configuration from YAML file"""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = """
workspace:
  base_path: "/test/workspace"
  input_dir: "test_input"
  processed_dir: "test_processed"
  transcribed_dir: "test_transcribed"

processing:
  silence_threshold: 0.02
  min_silence_duration: 30.0
  output_format: "wav"

transcription:
  default_model: "whisper-base"
  max_concurrent: 5
  chunk_processing: false
"""
            f.write(yaml_content)
            temp_path = Path(f.name)
        
        try:
            # Load config from file
            config = UnifiedConfig(config_path=temp_path)
            
            # Verify loaded values
            assert config.workspace.base_path == Path("/test/workspace")
            assert config.workspace.input_dir == "test_input"
            assert config.processing.silence_threshold == 0.02
            assert config.processing.min_silence_duration == 30.0
            assert config.transcription.default_model == "whisper-base"
            assert config.transcription.max_concurrent == 5
            assert config.transcription.chunk_processing is False
        finally:
            # Clean up
            temp_path.unlink()
    
    def test_partial_yaml_loading(self):
        """Test loading partial configuration from YAML"""
        # Create temporary config file with only some sections
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = """
processing:
  silence_threshold: 0.03
  output_format: "mp3"
"""
            f.write(yaml_content)
            temp_path = Path(f.name)
        
        try:
            config = UnifiedConfig(config_path=temp_path)
            
            # Check modified values
            assert config.processing.silence_threshold == 0.03
            assert config.processing.output_format == "mp3"
            
            # Check defaults are preserved for other configs
            assert config.workspace.base_path == Path.home() / "neuravox"
            assert config.transcription.default_model == "google-gemini"
        finally:
            temp_path.unlink()
    
    def test_invalid_config_path(self):
        """Test behavior with non-existent config file"""
        # Should not raise error, just use defaults
        config = UnifiedConfig(config_path=Path("/non/existent/path.yaml"))
        
        # Should have all defaults
        assert config.workspace.base_path == Path.home() / "neuravox"
        assert config.processing.silence_threshold == 0.01
        assert config.transcription.default_model == "google-gemini"
    
    def test_save_config(self):
        """Test saving configuration to file"""
        config = UnifiedConfig()
        
        # Modify some values
        config.processing.silence_threshold = 0.05
        config.transcription.max_concurrent = 10
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            config.save(temp_path)
            
            # Load saved config
            with open(temp_path) as f:
                saved_data = yaml.safe_load(f)
            
            # Verify saved values
            assert saved_data['processing']['silence_threshold'] == 0.05
            assert saved_data['transcription']['max_concurrent'] == 10
        finally:
            temp_path.unlink()
    
    def test_config_hierarchy(self):
        """Test configuration hierarchy (env vars > config file > defaults)"""
        # Set env var
        os.environ['GOOGLE_API_KEY'] = "env_var_key"
        
        # Create config file with different key
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = """
api_keys:
  google_api_key: "config_file_key"
"""
            f.write(yaml_content)
            temp_path = Path(f.name)
        
        try:
            config = UnifiedConfig(config_path=temp_path)
            
            # Env var should take precedence
            assert config.api_keys.google_api_key == "env_var_key"
        finally:
            del os.environ['GOOGLE_API_KEY']
            temp_path.unlink()


class TestConfigValidation:
    """Test configuration validation"""
    
    def test_invalid_silence_threshold(self):
        """Test validation of silence threshold values"""
        # Should accept valid values
        config = ProcessingConfig(silence_threshold=0.001)
        assert config.silence_threshold == 0.001
        
        # Should reject invalid values (this would need to be implemented)
        # with pytest.raises(ValueError):
        #     ProcessingConfig(silence_threshold=-0.01)
    
    def test_invalid_output_format(self):
        """Test validation of output format"""
        # Should accept valid formats
        for format in ['wav', 'flac', 'mp3']:
            config = ProcessingConfig(output_format=format)
            assert config.output_format == format
        
        # Should reject invalid formats (this would need to be implemented)
        # with pytest.raises(ValueError):
        #     ProcessingConfig(output_format='invalid')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])