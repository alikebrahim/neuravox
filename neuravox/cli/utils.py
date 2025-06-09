"""Common utilities for CLI commands"""

from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.prompt import Confirm

from neuravox.shared.config import UnifiedConfig
from neuravox.shared.file_utils import get_audio_files
from neuravox.constants import FileFormats


def load_config(config_path: Optional[Path] = None) -> UnifiedConfig:
    """Load and return unified configuration"""
    return UnifiedConfig(config_path=config_path)


def validate_files_input(
    files: Optional[List[Path]], 
    config: UnifiedConfig, 
    for_transcription: bool = False
) -> List[Path]:
    """
    Validate and return list of audio files for processing
    
    Args:
        files: Optional list of file paths
        config: Unified configuration
        for_transcription: Whether files are for transcription (uses transcribed_path)
        
    Returns:
        List of valid audio file paths
    """
    if files:
        # Use provided files, validate they exist and are audio files
        validated_files = []
        for file_path in files:
            if not file_path.exists():
                raise typer.BadParameter(f"File not found: {file_path}")
            
            if file_path.suffix.lower() not in FileFormats.AUDIO_EXTENSIONS:
                raise typer.BadParameter(f"Not an audio file: {file_path}")
            
            validated_files.append(file_path)
        return validated_files
    else:
        # Use files from workspace directory
        source_dir = config.transcribed_path if for_transcription else config.input_path
        audio_files = get_audio_files(source_dir)
        
        if not audio_files:
            dir_name = "transcribed" if for_transcription else "input"
            raise typer.BadParameter(f"No audio files found in {dir_name} directory: {source_dir}")
        
        return audio_files


def get_confirmation(message: str, console: Console) -> bool:
    """Get user confirmation with consistent styling"""
    return Confirm.ask(f"[yellow]{message}[/yellow]", console=console)


def validate_audio_file(file_path: Path) -> bool:
    """Check if file is a valid audio file"""
    return (file_path.exists() and 
            file_path.is_file() and 
            file_path.suffix.lower() in FileFormats.AUDIO_EXTENSIONS)