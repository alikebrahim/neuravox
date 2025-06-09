"""Interactive mode handling for CLI commands"""

from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm, FloatPrompt, IntPrompt

from neuravox.shared.config import ProcessingConfig, TranscriptionConfig, UnifiedConfig
from neuravox.shared.file_utils import get_audio_files
from neuravox.constants import AudioProcessing, TranscriptionDefaults, ModelIdentifiers


class InteractiveManager:
    """Handles interactive configuration and file selection"""
    
    def __init__(self, console: Console):
        self.console = console
    
    def configure_processing(self, config: ProcessingConfig) -> ProcessingConfig:
        """Interactive configuration for audio processing parameters"""
        self.console.print("[bold blue]Audio Processing Configuration[/bold blue]")
        
        # Silence threshold
        silence_threshold = FloatPrompt.ask(
            "Silence threshold (lower = more sensitive)",
            default=config.silence_threshold,
            console=self.console
        )
        
        # Minimum silence duration
        min_silence_duration = FloatPrompt.ask(
            "Minimum silence duration (seconds)",
            default=config.min_silence_duration,
            console=self.console
        )
        
        # Sample rate
        sample_rate = IntPrompt.ask(
            "Sample rate (Hz)",
            default=config.sample_rate,
            console=self.console
        )
        
        # Output format
        format_choices = ["flac", "wav", "mp3"]
        output_format = Prompt.ask(
            "Output format",
            choices=format_choices,
            default=config.output_format,
            console=self.console
        )
        
        # Normalize audio
        normalize = Confirm.ask(
            "Normalize audio levels?",
            default=config.normalize,
            console=self.console
        )
        
        return ProcessingConfig(
            silence_threshold=silence_threshold,
            min_silence_duration=min_silence_duration,
            sample_rate=sample_rate,
            output_format=output_format,
            normalize=normalize,
            compression_level=config.compression_level,
            chunk_boundary=config.chunk_boundary
        )
    
    def configure_transcription(self, config: TranscriptionConfig) -> TranscriptionConfig:
        """Interactive configuration for transcription parameters"""
        self.console.print("[bold blue]Transcription Configuration[/bold blue]")
        
        # Model selection handled separately
        
        # Max concurrent
        max_concurrent = IntPrompt.ask(
            "Maximum concurrent transcriptions",
            default=config.max_concurrent,
            console=self.console
        )
        
        # Chunk processing
        chunk_processing = Confirm.ask(
            "Process files in chunks?",
            default=config.chunk_processing,
            console=self.console
        )
        
        # Combine chunks
        combine_chunks = Confirm.ask(
            "Combine chunk transcriptions?",
            default=config.combine_chunks,
            console=self.console
        )
        
        # Include timestamps
        include_timestamps = Confirm.ask(
            "Include timestamps in output?",
            default=config.include_timestamps,
            console=self.console
        )
        
        return TranscriptionConfig(
            default_model=config.default_model,  # Set separately
            max_concurrent=max_concurrent,
            chunk_processing=chunk_processing,
            combine_chunks=combine_chunks,
            include_timestamps=include_timestamps
        )
    
    def select_model(self, config: UnifiedConfig) -> str:
        """Interactive model selection"""
        available_models = config.list_models()
        
        if len(available_models) == 1:
            return available_models[0]
        
        self.console.print("[bold blue]Available Models:[/bold blue]")
        for i, model_key in enumerate(available_models, 1):
            model_config = config.get_model(model_key)
            if model_config:
                self.console.print(f"  {i}. {model_config.name} ({model_key})")
            else:
                self.console.print(f"  {i}. {model_key}")
        
        while True:
            try:
                choice = IntPrompt.ask(
                    "Select model",
                    default=1,
                    console=self.console
                )
                if 1 <= choice <= len(available_models):
                    return available_models[choice - 1]
                else:
                    self.console.print("[red]Invalid choice. Please try again.[/red]")
            except (ValueError, IndexError):
                self.console.print("[red]Invalid input. Please enter a number.[/red]")
    
    def select_files(self, config: UnifiedConfig, for_transcription: bool = False) -> List[Path]:
        """Interactive file selection"""
        source_dir = config.transcribed_path if for_transcription else config.input_path
        dir_name = "transcribed" if for_transcription else "input"
        
        audio_files = get_audio_files(source_dir)
        
        if not audio_files:
            self.console.print(f"[red]No audio files found in {dir_name} directory: {source_dir}[/red]")
            return []
        
        if len(audio_files) == 1:
            self.console.print(f"Found 1 audio file in {dir_name} directory")
            return audio_files
        
        self.console.print(f"[bold blue]Found {len(audio_files)} audio files in {dir_name} directory:[/bold blue]")
        for i, file_path in enumerate(audio_files, 1):
            self.console.print(f"  {i}. {file_path.name}")
        
        # Ask if user wants to process all files
        process_all = Confirm.ask(
            f"Process all {len(audio_files)} files?",
            default=True,
            console=self.console
        )
        
        if process_all:
            return audio_files
        
        # Let user select specific files
        selected_files = []
        while True:
            try:
                choice = Prompt.ask(
                    "Enter file numbers (comma-separated, or 'done' to finish)",
                    console=self.console
                )
                
                if choice.lower() == 'done':
                    break
                
                # Parse comma-separated numbers
                file_numbers = [int(x.strip()) for x in choice.split(',')]
                
                for num in file_numbers:
                    if 1 <= num <= len(audio_files):
                        file_path = audio_files[num - 1]
                        if file_path not in selected_files:
                            selected_files.append(file_path)
                            self.console.print(f"  ✓ Added: {file_path.name}")
                    else:
                        self.console.print(f"[red]Invalid file number: {num}[/red]")
                
            except ValueError:
                self.console.print("[red]Invalid input. Please enter numbers separated by commas.[/red]")
        
        return selected_files
    
    def get_output_directory(self, default_dir: Path, prompt_text: str) -> Path:
        """Interactive output directory selection"""
        use_default = Confirm.ask(
            f"Use default {prompt_text} directory ({default_dir})?",
            default=True,
            console=self.console
        )
        
        if use_default:
            return default_dir
        
        while True:
            custom_path = Prompt.ask(
                f"Enter custom {prompt_text} directory path",
                console=self.console
            )
            
            try:
                path = Path(custom_path).expanduser().resolve()
                if not path.exists():
                    create_dir = Confirm.ask(
                        f"Directory doesn't exist. Create it?",
                        default=True,
                        console=self.console
                    )
                    if create_dir:
                        path.mkdir(parents=True, exist_ok=True)
                        return path
                else:
                    return path
            except Exception as e:
                self.console.print(f"[red]Invalid path: {e}[/red]")