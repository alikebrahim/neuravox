"""
Unified CLI for Neuravox platform with modular command structure
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
import time

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, FloatPrompt, IntPrompt, Prompt
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

from neuravox.core.pipeline import AudioPipeline
from neuravox.processor.audio_splitter import AudioProcessor
from neuravox.transcriber.engine import AudioTranscriber
from neuravox.shared.config import ProcessingConfig, TranscriptionConfig, UnifiedConfig
from neuravox.shared.file_utils import format_file_size, get_audio_files
from neuravox.shared.progress import UnifiedProgressTracker

app = typer.Typer(
    name="neuravox",
    help="Neuravox - Advanced audio processing and transcription platform",
    rich_markup_mode="rich",
)
console = Console()


@app.command()
def init(
    workspace: Optional[Path] = typer.Option(
        None, "--workspace", "-w", help="Workspace directory path"
    ),
):
    """Initialize workspace directories"""
    config = UnifiedConfig()

    if workspace:
        config.workspace = Path(workspace).expanduser()

    # Create workspace directories
    config.ensure_workspace_dirs()

    console.print(
        Panel(
            f"[green]✓ Workspace initialized at {config.workspace}[/green]\n\n"
            f"Directories created:\n"
            f"  • Input: {config.input_path}\n"
            f"  • Processed: {config.processed_path}\n"
            f"  • Transcribed: {config.transcribed_path}",
            title="Workspace Initialized",
            border_style="green",
        )
    )


@app.command()
def process(
    files: Optional[List[Path]] = typer.Argument(None, help="Audio files to process"),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Interactive configuration"
    ),
    silence_threshold: Optional[float] = typer.Option(
        None, "--silence-threshold", help="Silence detection threshold"
    ),
    min_silence_duration: Optional[float] = typer.Option(
        None, "--min-silence", help="Minimum silence duration in seconds"
    ),
    output_format: Optional[str] = typer.Option(
        None, "--format", help="Output format (flac, wav, mp3)"
    ),
    config_path: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Configuration file path"
    ),
):
    """Process audio files (splitting only)"""
    config = UnifiedConfig(config_path) if config_path else UnifiedConfig()
    
    if interactive:
        # Interactive configuration
        console.print("\n[bold cyan]🎵 Neuravox Audio Processing[/bold cyan]")
        
        # File selection
        selected_files = files or _interactive_file_selection(config)
        if not selected_files:
            return
            
        # Processing configuration
        processing_config = _interactive_processing_config(config.processing, console)
        
        # Apply overrides
        config.processing = processing_config
        files = selected_files
    else:
        # Apply CLI parameter overrides
        if silence_threshold is not None:
            config.processing.silence_threshold = silence_threshold
        if min_silence_duration is not None:
            config.processing.min_silence_duration = min_silence_duration
        if output_format is not None:
            config.processing.output_format = output_format
            
        # File validation
        if not files:
            files = _interactive_file_selection(config)
            if not files:
                return
                
        files = _validate_audio_files(files)
        if not files:
            return

    # Create audio processor
    processor = AudioProcessor(
        silence_threshold=config.processing.silence_threshold,
        min_silence_duration=config.processing.min_silence_duration,
        pipeline_mode=False,  # Standalone processing mode
    )

    console.print(f"\n[bold]Processing {len(files)} file(s)[/bold]")
    console.print(f"Output format: {config.processing.output_format}")
    console.print(f"Workspace: {config.processed_path}\n")

    if not Confirm.ask("Continue with audio processing?"):
        console.print("[yellow]Processing cancelled[/yellow]")
        return

    # Process files
    results = []
    with UnifiedProgressTracker(console) as tracker:
        for file_path in files:
            task_id = tracker.add_task("processing", f"Processing {file_path.name}", 100)
            
            try:
                start_time = time.time()
                output_dir = config.processed_path / file_path.stem
                output_dir.mkdir(parents=True, exist_ok=True)
                
                metadata = processor.process_file(file_path, output_dir)
                processing_time = time.time() - start_time
                
                tracker.finish_task(task_id)
                
                results.append({
                    "file": file_path.name,
                    "status": "completed",
                    "chunks": len(metadata.chunks) if metadata.chunks else 0,
                    "processing_time": processing_time,
                    "output_dir": output_dir
                })
                
            except Exception as e:
                tracker.finish_task(task_id)
                results.append({
                    "file": file_path.name,
                    "status": "failed",
                    "error": str(e)
                })

    _display_processing_results(results)


@app.command()
def transcribe(
    files: Optional[List[Path]] = typer.Argument(None, help="Audio files to transcribe"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Transcription model"),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Interactive configuration"
    ),
    chunk_processing: Optional[bool] = typer.Option(
        None, "--chunks", help="Process chunks separately"
    ),
    include_timestamps: Optional[bool] = typer.Option(
        None, "--timestamps", help="Include timestamps in output"
    ),
    config_path: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Configuration file path"
    ),
):
    """Transcribe audio files or chunks"""
    config = UnifiedConfig(config_path) if config_path else UnifiedConfig()
    
    if interactive:
        # Interactive configuration
        console.print("\n[bold cyan]🎵 Neuravox Audio Transcription[/bold cyan]")
        
        # File selection
        selected_files = files or _interactive_file_selection(config, for_transcription=True)
        if not selected_files:
            return
            
        # Model selection
        selected_model = _interactive_model_selection(config, console)
        
        # Transcription configuration
        transcription_config = _interactive_transcription_config(config.transcription, console)
        
        # Apply overrides
        config.transcription = transcription_config
        model = selected_model
        files = selected_files
    else:
        # Apply CLI parameter overrides
        if chunk_processing is not None:
            config.transcription.chunk_processing = chunk_processing
        if include_timestamps is not None:
            config.transcription.include_timestamps = include_timestamps
            
        model = model or config.transcription.default_model
        
        # File validation
        if not files:
            files = _interactive_file_selection(config, for_transcription=True)
            if not files:
                return
                
        files = _validate_audio_files(files)
        if not files:
            return

    # Create transcriber
    transcriber = AudioTranscriber(config)
    
    # Validate model
    if not transcriber.validate_model(model):
        console.print(f"[red]Model '{model}' is not available or properly configured[/red]")
        return

    console.print(f"\n[bold]Transcribing {len(files)} file(s)[/bold]")
    console.print(f"Model: {model}")
    console.print(f"Workspace: {config.transcribed_path}\n")

    if not Confirm.ask("Continue with transcription?"):
        console.print("[yellow]Transcription cancelled[/yellow]")
        return

    # Process files
    async def run_transcription():
        results = []
        for file_path in files:
            try:
                start_time = time.time()
                output_dir = config.transcribed_path / file_path.stem
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Simple transcription (not using pipeline chunks)
                result = await transcriber.transcribe_file(file_path, model, output_dir)
                transcription_time = time.time() - start_time
                
                results.append({
                    "file": file_path.name,
                    "status": "completed",
                    "transcription_time": transcription_time,
                    "output_dir": output_dir,
                    "result": result
                })
                
            except Exception as e:
                results.append({
                    "file": file_path.name,
                    "status": "failed",
                    "error": str(e)
                })
        
        _display_transcription_results(results)
    
    asyncio.run(run_transcription())


@app.command()
def convert(
    files: Optional[List[Path]] = typer.Argument(None, help="Audio files to convert"),
    format: str = typer.Option("flac", "--format", "-f", help="Target format"),
    quality: Optional[str] = typer.Option(None, "--quality", "-q", help="Quality setting"),
    sample_rate: Optional[int] = typer.Option(None, "--sample-rate", help="Target sample rate"),
    normalize: bool = typer.Option(False, "--normalize", help="Normalize audio levels"),
    config_path: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Configuration file path"
    ),
):
    """Convert audio files to different formats"""
    config = UnifiedConfig(config_path) if config_path else UnifiedConfig()
    
    # File validation
    if not files:
        files = _interactive_file_selection(config)
        if not files:
            return
            
    files = _validate_audio_files(files)
    if not files:
        return

    console.print(f"\n[bold]Converting {len(files)} file(s)[/bold]")
    console.print(f"Target format: {format}")
    if quality:
        console.print(f"Quality: {quality}")
    if sample_rate:
        console.print(f"Sample rate: {sample_rate}Hz")
    console.print(f"Normalize: {normalize}")
    console.print(f"Output: {config.processed_path}\n")

    if not Confirm.ask("Continue with conversion?"):
        console.print("[yellow]Conversion cancelled[/yellow]")
        return

    # Use audio processor for conversion
    processor = AudioProcessor(pipeline_mode=False)
    
    results = []
    with UnifiedProgressTracker(console) as tracker:
        for file_path in files:
            task_id = tracker.add_task("converting", f"Converting {file_path.name}", 100)
            
            try:
                start_time = time.time()
                output_dir = config.processed_path / file_path.stem
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Use dedicated convert_file method
                converted_file = output_dir / f"{file_path.stem}.{format}"
                result = processor.convert_file(
                    input_file=file_path,
                    output_file=converted_file,
                    format=format,
                    quality=quality,
                    sample_rate=sample_rate,
                    normalize=normalize
                )
                
                tracker.finish_task(task_id)
                
                if result["status"] == "success":
                    results.append({
                        "file": file_path.name,
                        "status": "completed",
                        "conversion_time": result["conversion_time"],
                        "output_file": converted_file,
                        "compression_ratio": result["compression_ratio"]
                    })
                else:
                    results.append({
                        "file": file_path.name,
                        "status": "failed",
                        "error": result["error"]
                    })
                
            except Exception as e:
                tracker.finish_task(task_id)
                results.append({
                    "file": file_path.name,
                    "status": "failed",
                    "error": str(e)
                })

    _display_conversion_results(results)


@app.command()
def pipeline(
    files: Optional[List[Path]] = typer.Argument(None, help="Audio files to process"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Transcription model"),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Interactive file selection and configuration"
    ),
    config_path: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Configuration file path"
    ),
):
    """Process audio files through full pipeline (processing + transcription)"""
    # This is the original process command functionality
    config = UnifiedConfig(config_path) if config_path else UnifiedConfig()

    # Enhanced interactive mode or simple processing
    if interactive:
        # Enhanced interactive flow
        console.print("\n[bold cyan]🎵 Neuravox Interactive Pipeline[/bold cyan]")

        # Step 1: File selection
        selected_files = _interactive_file_selection(config)
        if not selected_files:
            return

        # Step 2: Processing configuration
        processing_config = _interactive_processing_config(config.processing, console)

        # Step 3: Model selection
        selected_model = _interactive_model_selection(config, console)

        # Step 4: Transcription configuration
        transcription_config = _interactive_transcription_config(config.transcription, console)

        # Step 5: Settings preview and confirmation loop
        while True:
            action = _show_settings_preview(
                processing_config, transcription_config, selected_model, selected_files, console
            )

            if action == "proceed":
                break
            elif action == "modify-files":
                selected_files = _interactive_file_selection(config)
                if not selected_files:
                    return
            elif action == "modify-processing":
                processing_config = _interactive_processing_config(processing_config, console)
            elif action == "modify-model":
                selected_model = _interactive_model_selection(config, console)
            elif action == "modify-transcription":
                transcription_config = _interactive_transcription_config(
                    transcription_config, console
                )
            elif action == "cancel":
                console.print("[yellow]Operation cancelled[/yellow]")
                return

        # Apply overrides to config BEFORE creating pipeline
        config = _apply_interactive_overrides(config, processing_config, transcription_config)
        model = selected_model
        files = selected_files
        
        # Create pipeline with final configuration
        pipeline = AudioPipeline(config)

    else:
        # Simple mode: get files to process
        if not files:
            files = _interactive_file_selection(config)
            if not files:
                return

        files = _validate_audio_files(files)
        if not files:
            return

        # Show processing plan
        console.print(f"\n[bold]Processing {len(files)} file(s) through full pipeline[/bold]")
        console.print(f"Model: {model or config.transcription.default_model}")
        console.print(f"Workspace: {config.workspace}\n")

        if not Confirm.ask("Continue with pipeline processing?"):
            console.print("[yellow]Processing cancelled[/yellow]")
            return
            
        # Create pipeline with original configuration for non-interactive mode
        pipeline = AudioPipeline(config)

    # Process files
    async def run_pipeline():
        # Let UnifiedProgressTracker handle all progress display
        results = await pipeline.process_batch(files, model)

        # Show results
        _display_results(results)

    asyncio.run(run_pipeline())


@app.command()
def status(
    config_path: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Configuration file path"
    ),
):
    """Show pipeline status and recent activity"""
    config = UnifiedConfig(config_path) if config_path else UnifiedConfig()
    pipeline = AudioPipeline(config)

    summary = pipeline.get_status()

    # Display status counts
    console.print(
        Panel(
            f"[bold]Pipeline Status[/bold]\n\n"
            f"Total files: {summary['total_files']}\n"
            f"Completed: {summary['status_counts'].get('completed', 0)}\n"
            f"Processing: {summary['status_counts'].get('processing', 0)}\n"
            f"Failed: {summary['status_counts'].get('failed', 0)}",
            title="Status Summary",
            border_style="blue",
        )
    )

    # Display recent activity
    if summary["recent_activity"]:
        table = Table(title="Recent Activity")
        table.add_column("File ID", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Updated", style="green")

        for activity in summary["recent_activity"]:
            table.add_row(activity["file_id"], activity["status"], activity["updated_at"])

        console.print(table)


@app.command()
def resume(
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Transcription model"),
    config_path: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Configuration file path"
    ),
):
    """Resume failed processing"""
    config = UnifiedConfig(config_path) if config_path else UnifiedConfig()
    pipeline = AudioPipeline(config)

    failed_files = pipeline.resume_failed()
    if not failed_files:
        console.print("[green]No failed files to resume[/green]")
        return

    # Display failed files
    table = Table(title="Failed Files")
    table.add_column("File ID", style="cyan")
    table.add_column("Original Path", style="magenta")
    table.add_column("Error", style="red")

    for file_info in failed_files:
        table.add_row(
            file_info["file_id"],
            Path(file_info["original_path"]).name,
            file_info.get("error_message", "Unknown error")[:50] + "...",
        )

    console.print(table)

    if Confirm.ask(f"\nResume processing {len(failed_files)} failed file(s)?"):
        files = [Path(f["original_path"]) for f in failed_files]

        async def run_resume():
            results = await pipeline.process_batch(files, model)
            _display_results(results)

        asyncio.run(run_resume())


@app.command()
def config(
    show: bool = typer.Option(False, "--show", "-s", help="Show current configuration"),
    edit: bool = typer.Option(False, "--edit", "-e", help="Edit configuration"),
    config_path: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Configuration file path"
    ),
):
    """Manage configuration"""
    config = UnifiedConfig(config_path) if config_path else UnifiedConfig()

    if show:
        # Display current configuration
        console.print(
            Panel(
                f"[bold]Current Configuration[/bold]\n\n"
                f"[yellow]Workspace:[/yellow]\n"
                f"  Path: {config.workspace}\n"
                f"  Input: {config.input_path}\n"
                f"  Processed: {config.processed_path}\n"
                f"  Transcribed: {config.transcribed_path}\n\n"
                f"[yellow]Processing:[/yellow]\n"
                f"  Silence threshold: {config.processing.silence_threshold}\n"
                f"  Min silence duration: {config.processing.min_silence_duration}s\n"
                f"  Sample rate: {config.processing.sample_rate} Hz\n"
                f"  Output format: {config.processing.output_format}\n\n"
                f"[yellow]Transcription:[/yellow]\n"
                f"  Default model: {config.transcription.default_model}\n"
                f"  Max concurrent: {config.transcription.max_concurrent}\n"
                f"  Chunk processing: {config.transcription.chunk_processing}\n"
                f"  Combine chunks: {config.transcription.combine_chunks}",
                title="Configuration",
                border_style="blue",
            )
        )

    elif edit:
        # Interactive configuration editing
        console.print("[yellow]Configuration editing not yet implemented[/yellow]")
        console.print("Please edit the configuration file directly:")
        console.print(f"  {config.config_path}")


# Helper functions (preserved from original)
def _interactive_processing_config(
    current_config: ProcessingConfig, console: Console
) -> ProcessingConfig:
    """Interactive configuration of audio processing settings."""
    console.print("\n[bold cyan]Audio Processing Configuration[/bold cyan]")
    console.print("Current settings:")
    console.print(f"  Silence threshold: {current_config.silence_threshold}")
    console.print(f"  Min silence duration: {current_config.min_silence_duration}s")
    console.print(f"  Output format: {current_config.output_format}")
    console.print(f"  Sample rate: {current_config.sample_rate}Hz")
    console.print(f"  Normalization: {current_config.normalize}")

    use_defaults = Confirm.ask("Use default processing settings?", default=True)
    if use_defaults:
        return current_config

    # Interactive configuration of each setting
    silence_threshold = FloatPrompt.ask(
        "Silence threshold (0.001-1.0)", default=current_config.silence_threshold, show_default=True
    )

    min_silence_duration = FloatPrompt.ask(
        "Minimum silence duration (seconds)",
        default=current_config.min_silence_duration,
        show_default=True,
    )

    output_format = Prompt.ask(
        "Output format",
        choices=["flac", "wav", "mp3"],
        default=current_config.output_format,
        show_default=True,
    )

    sample_rate = Prompt.ask(
        "Sample rate (Hz)",
        choices=["16000", "22050", "44100"],
        default=str(current_config.sample_rate),
        show_default=True,
    )

    normalize = Confirm.ask("Normalize audio levels?", default=current_config.normalize)

    # Return new config with overrides
    return ProcessingConfig(
        silence_threshold=silence_threshold,
        min_silence_duration=min_silence_duration,
        output_format=output_format,
        sample_rate=int(sample_rate),
        normalize=normalize,
        compression_level=current_config.compression_level,
        chunk_boundary=current_config.chunk_boundary,
    )


def _interactive_model_selection(config: UnifiedConfig, console: Console) -> str:
    """Interactive selection of transcription model."""
    console.print("\n[bold cyan]Transcription Model Selection[/bold cyan]")

    models = list(config.models.keys())

    # Display model options with descriptions
    table = Table(title="Available Models")
    table.add_column("Index", style="cyan", width=6)
    table.add_column("Model", style="green")
    table.add_column("Description", style="white")

    for i, model_key in enumerate(models, 1):
        model_config = config.models[model_key]
        table.add_row(str(i), model_key, model_config.name)

    console.print(table)

    choice = IntPrompt.ask(f"Select model (1-{len(models)})", default=1)

    # Validate choice and return model key
    if 1 <= choice <= len(models):
        selected_model = models[choice - 1]
        console.print(f"✓ Selected: [green]{selected_model}[/green]")
        return selected_model
    else:
        console.print("[red]Invalid choice, using default[/red]")
        return config.transcription.default_model


def _interactive_transcription_config(
    current_config: TranscriptionConfig, console: Console
) -> TranscriptionConfig:
    """Interactive configuration of transcription settings."""
    console.print("\n[bold cyan]Transcription Configuration[/bold cyan]")
    console.print("Current settings:")
    console.print(f"  Chunk processing: {current_config.chunk_processing}")
    console.print(f"  Combine chunks: {current_config.combine_chunks}")
    console.print(f"  Include timestamps: {current_config.include_timestamps}")
    console.print(f"  Max concurrent: {current_config.max_concurrent}")

    use_defaults = Confirm.ask("Use default transcription settings?", default=True)
    if use_defaults:
        return current_config

    chunk_processing = Confirm.ask(
        "Process audio chunks separately?", default=current_config.chunk_processing
    )

    combine_chunks = current_config.combine_chunks
    if chunk_processing:
        combine_chunks = Confirm.ask(
            "Combine chunk results into single output?", default=current_config.combine_chunks
        )

    include_timestamps = Confirm.ask(
        "Include timestamps in output?", default=current_config.include_timestamps
    )

    max_concurrent = IntPrompt.ask(
        "Maximum concurrent transcriptions",
        default=current_config.max_concurrent,
        show_default=True,
    )

    return TranscriptionConfig(
        default_model=current_config.default_model,
        max_concurrent=max_concurrent,
        chunk_processing=chunk_processing,
        combine_chunks=combine_chunks,
        include_timestamps=include_timestamps,
    )


def _show_settings_preview(
    processing_config: ProcessingConfig,
    transcription_config: TranscriptionConfig,
    selected_model: str,
    selected_files: List[Path],
    console: Console,
) -> str:
    """Display final configuration and get user confirmation."""
    console.print("\n[bold green]Configuration Summary[/bold green]")

    # Files section
    console.print(f"\n[bold]Files to Process:[/bold] {len(selected_files)} files")
    for file_path in selected_files[:3]:  # Show first 3 files
        console.print(f"  • {file_path.name}")
    if len(selected_files) > 3:
        console.print(f"  ... and {len(selected_files) - 3} more")

    # Processing section
    console.print("\n[bold]Audio Processing:[/bold]")
    console.print(f"  Silence threshold: {processing_config.silence_threshold}")
    console.print(f"  Min silence duration: {processing_config.min_silence_duration}s")
    console.print(f"  Output format: {processing_config.output_format}")
    console.print(f"  Sample rate: {processing_config.sample_rate}Hz")
    console.print(f"  Normalization: {processing_config.normalize}")

    # Transcription section
    console.print("\n[bold]Transcription:[/bold]")
    console.print(f"  Model: {selected_model}")
    console.print(f"  Chunk processing: {transcription_config.chunk_processing}")
    console.print(f"  Include timestamps: {transcription_config.include_timestamps}")
    console.print(f"  Max concurrent: {transcription_config.max_concurrent}")

    console.print("\n[dim]You can go back to modify any section.[/dim]")

    actions = [
        "proceed",
        "modify-files",
        "modify-processing",
        "modify-model",
        "modify-transcription",
        "cancel",
    ]

    action = Prompt.ask("Action", choices=actions, default="proceed", show_default=True)

    return action


def _apply_interactive_overrides(
    base_config: UnifiedConfig,
    processing_overrides: ProcessingConfig,
    transcription_overrides: TranscriptionConfig,
) -> UnifiedConfig:
    """Apply interactive overrides to base configuration."""
    import copy

    # Create deep copy of base config
    new_config = copy.deepcopy(base_config)

    # Apply overrides
    new_config.processing = processing_overrides
    new_config.transcription = transcription_overrides

    return new_config


def _interactive_file_selection(config: UnifiedConfig, for_transcription: bool = False) -> List[Path]:
    """Interactive file selection from input directory or processed directory"""
    if for_transcription:
        # Look for audio files in both input and processed directories
        input_files = get_audio_files(config.input_path)
        processed_files = []
        if config.processed_path.exists():
            processed_files = get_audio_files(config.processed_path)
        
        audio_files = input_files + processed_files
        location_desc = "input and processed directories"
    else:
        audio_files = get_audio_files(config.input_path)
        location_desc = "input directory"

    if not audio_files:
        console.print(f"[yellow]No audio files found in {location_desc}[/yellow]")
        return []

    # Display available files
    table = Table(title="Available Audio Files")
    table.add_column("Index", style="cyan", width=6)
    table.add_column("File Name", style="magenta")
    table.add_column("Size", style="green", width=10)
    table.add_column("Location", style="blue", width=12)

    for i, file in enumerate(audio_files):
        size = format_file_size(file.stat().st_size)
        location = "processed" if str(file).find("processed") != -1 else "input"
        table.add_row(str(i + 1), file.name, size, location)

    console.print(table)

    # Get selection
    selection = Prompt.ask(
        "\nSelect files to process (comma-separated indices, ranges like 1-3, or 'all')",
        default="all",
    )

    if selection.lower() == "all":
        return audio_files

    # Parse selection (convert 1-based input to 0-based indices)
    selected_indices = []
    for part in selection.split(","):
        part = part.strip()
        if "-" in part:
            # Range
            start, end = part.split("-")
            # Convert 1-based to 0-based
            selected_indices.extend(range(int(start) - 1, int(end)))
        else:
            # Single index - convert 1-based to 0-based
            selected_indices.append(int(part) - 1)

    # Get selected files
    selected_files = []
    for i in selected_indices:
        if 0 <= i < len(audio_files):
            selected_files.append(audio_files[i])

    return selected_files


def _validate_audio_files(files: List[Path]) -> List[Path]:
    """Validate all files exist and are audio files"""
    valid_files = []
    audio_extensions = {
        ".mp3", ".wav", ".flac", ".m4a", ".ogg", 
        ".opus", ".wma", ".aac", ".mp4"
    }
    
    for file in files:
        if not file.exists():
            console.print(f"[red]File not found: {file}[/red]")
            continue
        if not file.is_file():
            console.print(f"[red]Not a file: {file}[/red]")
            continue
        if file.suffix.lower() not in audio_extensions:
            console.print(f"[red]Unsupported format: {file.suffix} ({file.name})[/red]")
            continue
        valid_files.append(file)

    if not valid_files:
        console.print("[red]No valid audio files to process[/red]")
        
    return valid_files


def _display_processing_results(results: List[Dict[str, Any]]):
    """Display audio processing results"""
    success_count = sum(1 for r in results if r["status"] == "completed")
    failed_count = sum(1 for r in results if r["status"] == "failed")

    # Summary
    console.print(
        Panel(
            f"[bold]Audio Processing Complete[/bold]\n\n"
            f"Total files: {len(results)}\n"
            f"[green]Successful: {success_count}[/green]\n"
            f"[red]Failed: {failed_count}[/red]",
            title="Processing Results",
            border_style="blue" if failed_count == 0 else "yellow",
        )
    )

    # Details table
    if results:
        table = Table(title="Processing Details")
        table.add_column("File", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Chunks", style="green")
        table.add_column("Time", style="yellow")
        table.add_column("Output", style="blue")

        for result in results:
            status_style = "green" if result["status"] == "completed" else "red"
            chunks_str = str(result.get("chunks", 0)) if result["status"] == "completed" else "N/A"
            time_str = f"{result.get('processing_time', 0):.1f}s" if "processing_time" in result else "N/A"
            output_str = str(result.get("output_dir", "")) if result["status"] == "completed" else result.get("error", "")

            table.add_row(
                result["file"],
                f"[{status_style}]{result['status']}[/{status_style}]",
                chunks_str,
                time_str,
                output_str,
            )

        console.print(table)


def _display_transcription_results(results: List[Dict[str, Any]]):
    """Display transcription results"""
    success_count = sum(1 for r in results if r["status"] == "completed")
    failed_count = sum(1 for r in results if r["status"] == "failed")

    # Summary
    console.print(
        Panel(
            f"[bold]Transcription Complete[/bold]\n\n"
            f"Total files: {len(results)}\n"
            f"[green]Successful: {success_count}[/green]\n"
            f"[red]Failed: {failed_count}[/red]",
            title="Transcription Results",
            border_style="blue" if failed_count == 0 else "yellow",
        )
    )

    # Details table
    if results:
        table = Table(title="Transcription Details")
        table.add_column("File", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Time", style="yellow")
        table.add_column("Output", style="blue")

        for result in results:
            status_style = "green" if result["status"] == "completed" else "red"
            time_str = f"{result.get('transcription_time', 0):.1f}s" if "transcription_time" in result else "N/A"
            output_str = str(result.get("output_dir", "")) if result["status"] == "completed" else result.get("error", "")

            table.add_row(
                result["file"],
                f"[{status_style}]{result['status']}[/{status_style}]",
                time_str,
                output_str,
            )

        console.print(table)


def _display_conversion_results(results: List[Dict[str, Any]]):
    """Display conversion results"""
    success_count = sum(1 for r in results if r["status"] == "completed")
    failed_count = sum(1 for r in results if r["status"] == "failed")

    # Summary
    console.print(
        Panel(
            f"[bold]Conversion Complete[/bold]\n\n"
            f"Total files: {len(results)}\n"
            f"[green]Successful: {success_count}[/green]\n"
            f"[red]Failed: {failed_count}[/red]",
            title="Conversion Results",
            border_style="blue" if failed_count == 0 else "yellow",
        )
    )

    # Details table
    if results:
        table = Table(title="Conversion Details")
        table.add_column("File", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Time", style="yellow")
        table.add_column("Output", style="blue")

        for result in results:
            status_style = "green" if result["status"] == "completed" else "red"
            time_str = f"{result.get('conversion_time', 0):.1f}s" if "conversion_time" in result else "N/A"
            output_str = str(result.get("output_file", "")) if result["status"] == "completed" else result.get("error", "")

            table.add_row(
                result["file"],
                f"[{status_style}]{result['status']}[/{status_style}]",
                time_str,
                output_str,
            )

        console.print(table)


def _display_results(results: List[Dict[str, Any]]):
    """Display pipeline processing results (preserves original functionality)"""
    success_count = sum(1 for r in results if r["status"] == "completed")
    failed_count = sum(1 for r in results if r["status"] == "failed")

    # Summary
    console.print(
        Panel(
            f"[bold]Pipeline Processing Complete[/bold]\n\n"
            f"Total files: {len(results)}\n"
            f"[green]Successful: {success_count}[/green]\n"
            f"[red]Failed: {failed_count}[/red]",
            title="Results Summary",
            border_style="blue" if failed_count == 0 else "yellow",
        )
    )

    # Details table
    if results:
        table = Table(title="Processing Details")
        table.add_column("File", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Time", style="green")
        table.add_column("Details", style="yellow")

        for result in results:
            status_style = "green" if result["status"] == "completed" else "red"
            time_str = f"{result.get('total_time', 0):.1f}s" if "total_time" in result else "N/A"

            details = ""
            if result["status"] == "completed" and result.get("transcription_result"):
                chunks = result["transcription_result"].get("chunks", 0)
                details = f"{chunks} chunks transcribed"
            elif result["status"] == "failed":
                details = result.get("error", "Unknown error")[:40] + "..."

            table.add_row(
                result["file_id"],
                f"[{status_style}]{result['status']}[/{status_style}]",
                time_str,
                details,
            )

        console.print(table)


if __name__ == "__main__":
    app()