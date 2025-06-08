#!/usr/bin/env python3

"""
Enhanced Audio Splitter CLI with Typer and Rich
Modern command-line interface with optimal FLAC conversion for speech transcription
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum

import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, IntPrompt, FloatPrompt, Confirm
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)
from rich.panel import Panel
from rich import print as rprint
from pydantic import BaseModel, Field, ConfigDict

from audio_splitter import process_audio_files
from metadata_output import MultiFormatExporter

# Initialize Rich console
console = Console()

# Initialize Typer app
app = typer.Typer(
    name="audio-splitter",
    help="🎧 Audio Splitter with optimal FLAC conversion for speech transcription",
    rich_markup_mode="rich",
    add_completion=False,
)


class OutputFormat(str, Enum):
    """Supported output formats"""

    wav = "wav"
    flac = "flac"
    mp3 = "mp3"


class CompressionLevel(int, Enum):
    """FLAC compression levels with descriptions"""

    fastest = 0  # Fastest encoding, largest files
    fast = 2  # Fast encoding
    balanced = 5  # Default balance
    high = 8  # High compression (recommended)
    maximum = 12  # Maximum compression, slowest


class SampleRate(int, Enum):
    """Common sample rates for audio processing"""

    telephone = 8000  # Telephone quality
    speech = 16000  # Optimal for speech transcription
    cd_half = 22050  # Half CD quality
    cd = 44100  # CD quality
    studio = 48000  # Studio quality


class AudioConfig(BaseModel):
    """Type-safe configuration with validation"""

    model_config = ConfigDict(use_enum_values=True)

    # FLAC Optimization Settings
    target_sample_rate: SampleRate = Field(
        default=SampleRate.speech, description="Target sample rate for transcription"
    )
    flac_compression_level: CompressionLevel = Field(
        default=CompressionLevel.high, description="FLAC compression level"
    )
    output_format: OutputFormat = Field(
        default=OutputFormat.flac, description="Output audio format"
    )

    # Processing Settings
    silence_threshold: float = Field(
        default=0.01,
        ge=0.001,
        le=0.1,
        description="Amplitude threshold for silence detection",
    )
    min_silence_duration: float = Field(
        default=25.0, ge=1.0, description="Minimum silence duration to split (seconds)"
    )
    min_chunk_duration: float = Field(
        default=5.0, ge=1.0, description="Minimum chunk duration (seconds)"
    )
    keep_silence: float = Field(
        default=1.0, ge=0.0, description="Silence to keep at boundaries (seconds)"
    )
    chunk_duration: float = Field(
        default=30.0, ge=10.0, description="Processing chunk duration (seconds)"
    )

    # Output Settings
    create_metadata: bool = Field(default=True, description="Generate metadata files")
    preserve_timestamps: bool = Field(
        default=True, description="Preserve file timestamps"
    )
    move_processed: bool = Field(
        default=True, description="Move processed files to input/processed/"
    )

    def to_processing_config(self) -> Dict[str, Any]:
        """Convert to format expected by audio_splitter"""
        return {
            "sample_rate": 22050,  # Processing sample rate
            "target_sample_rate": self.target_sample_rate.value,
            "flac_compression_level": self.flac_compression_level.value,
            "chunk_duration": self.chunk_duration,
            "silence_threshold": self.silence_threshold,
            "min_silence_duration": self.min_silence_duration,
            "min_chunk_duration": self.min_chunk_duration,
            "keep_silence": self.keep_silence,
            "output_format": self.output_format.value,
            "create_metadata": self.create_metadata,
            "preserve_timestamps": self.preserve_timestamps,
        }


def load_config(config_file: Optional[Path] = None) -> AudioConfig:
    """Load configuration from file or use defaults"""
    if config_file and config_file.exists():
        try:
            with open(config_file, "r") as f:
                if config_file.suffix.lower() in [".yaml", ".yml"]:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)

            console.print(f"✓ Loaded configuration from: {config_file}")
            return AudioConfig(**data)
        except Exception as e:
            console.print(f"⚠️  Error loading config file {config_file}: {e}")
            console.print("Using default configuration")

    return AudioConfig()


def save_config(config: AudioConfig, config_file: Path):
    """Save configuration to file"""
    try:
        # Convert to dict with proper values
        config_data = {
            "target_sample_rate": config.target_sample_rate.value,
            "flac_compression_level": config.flac_compression_level.value,
            "output_format": config.output_format.value,
            "silence_threshold": config.silence_threshold,
            "min_silence_duration": config.min_silence_duration,
            "min_chunk_duration": config.min_chunk_duration,
            "keep_silence": config.keep_silence,
            "chunk_duration": config.chunk_duration,
            "create_metadata": config.create_metadata,
            "preserve_timestamps": config.preserve_timestamps,
        }

        with open(config_file, "w") as f:
            if config_file.suffix.lower() in [".yaml", ".yml"]:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            else:
                json.dump(config_data, f, indent=2)
        console.print(f"✓ Configuration saved to: {config_file}")
    except Exception as e:
        console.print(f"❌ Error saving config: {e}")


def show_config_table(config: AudioConfig):
    """Display configuration in a nice table"""
    table = Table(
        title="🔧 Audio Processing Configuration",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Parameter", style="cyan", width=25)
    table.add_column("Value", style="green", width=15)
    table.add_column("Description", style="dim", width=40)

    # FLAC Optimization
    table.add_row(
        "Target Sample Rate",
        f"{config.target_sample_rate.value} Hz",
        "Optimal for speech transcription",
    )
    table.add_row(
        "FLAC Compression",
        f"Level {config.flac_compression_level.value}",
        "Higher = smaller files, slower encoding",
    )
    table.add_row(
        "Output Format", config.output_format.value.upper(), "Audio file format"
    )

    # Processing Settings
    table.add_row("", "", "", style="dim")  # Separator
    table.add_row(
        "Silence Threshold",
        f"{config.silence_threshold}",
        "Lower = more sensitive silence detection",
    )
    table.add_row(
        "Min Silence Duration",
        f"{config.min_silence_duration}s",
        "Required silence length to create split",
    )
    table.add_row(
        "Min Chunk Duration",
        f"{config.min_chunk_duration}s",
        "Reject chunks shorter than this",
    )
    table.add_row(
        "Move Processed Files",
        "Yes" if config.move_processed else "No",
        "Move files to input/processed/ after processing",
    )

    console.print(table)


def interactive_config() -> AudioConfig:
    """Rich interactive configuration"""
    console.print("\n")
    console.print(
        Panel.fit(
            "🔧 [bold blue]Interactive Audio Splitter Configuration[/bold blue]\n"
            "Configure optimal settings for speech transcription and LLM processing",
            title="Configuration Setup",
            border_style="blue",
        )
    )

    config = AudioConfig()

    # FLAC Optimization Settings
    console.print("\n📊 [bold cyan]FLAC Optimization Settings[/bold cyan]")
    console.print("These settings optimize audio files for transcription by LLMs\n")

    # Sample Rate Selection
    console.print("Sample Rate Options:")
    console.print("  • 8000 Hz  - Telephone quality (minimal)")
    console.print("  • 16000 Hz - [green]Optimal for speech transcription[/green] ⭐")
    console.print("  • 22050 Hz - Higher quality speech")
    console.print("  • 44100 Hz - CD quality (unnecessary for speech)")

    sample_rate_choice = IntPrompt.ask(
        "\nSelect target sample rate",
        choices=["8000", "16000", "22050", "44100"],
        default=16000,
    )
    config.target_sample_rate = SampleRate(sample_rate_choice)

    # Compression Level
    console.print("\nFLAC Compression Levels:")
    console.print("  • 0  - Fastest encoding, largest files")
    console.print("  • 2  - Fast encoding")
    console.print("  • 5  - Balanced (default)")
    console.print("  • 8  - [green]High compression (recommended)[/green] ⭐")
    console.print("  • 12 - Maximum compression, slowest")

    compression_choice = IntPrompt.ask(
        "\nSelect FLAC compression level", choices=["0", "2", "5", "8", "12"], default=8
    )
    config.flac_compression_level = CompressionLevel(compression_choice)

    # Output Format
    format_choice = Prompt.ask(
        "\nOutput format", choices=["flac", "wav", "mp3"], default="flac"
    )
    config.output_format = OutputFormat(format_choice)

    # Silence Detection Settings
    console.print("\n🔇 [bold cyan]Silence Detection Settings[/bold cyan]")

    config.silence_threshold = FloatPrompt.ask(
        "Silence threshold (0.001=very sensitive, 0.1=less sensitive)", default=0.01
    )

    config.min_silence_duration = FloatPrompt.ask(
        "Minimum silence duration to create split (seconds)", default=25.0
    )

    # Advanced Settings
    if Confirm.ask("\nConfigure advanced settings?", default=False):
        console.print("\n⚙️ [bold cyan]Advanced Settings[/bold cyan]")

        config.min_chunk_duration = FloatPrompt.ask(
            "Minimum chunk duration (seconds)", default=5.0
        )

        config.keep_silence = FloatPrompt.ask(
            "Silence to keep at chunk boundaries (seconds)", default=1.0
        )

        config.chunk_duration = FloatPrompt.ask(
            "Processing chunk duration (seconds)", default=30.0
        )

        config.create_metadata = Confirm.ask("Generate metadata files?", default=True)
        
        config.move_processed = Confirm.ask(
            "Move processed files to input/processed/?", default=True
        )

    # Show configuration summary
    console.print("\n")
    show_config_table(config)

    # Save option
    if Confirm.ask("\n💾 Save this configuration to file?", default=False):
        save_path = Prompt.ask("Configuration filename", default="audio_config.yaml")
        save_config(config, Path(save_path))

    return config


@app.command()
def process(
    input_dir: Path = typer.Option(
        "input", "--input", "-i", help="Input directory containing audio files"
    ),
    output_dir: Path = typer.Option(
        "output", "--output", "-o", help="Output directory for processed files"
    ),
    config_file: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Configuration file (YAML or JSON)"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", help="Interactive configuration setup"
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.flac, "--format", "-f", help="Output format"
    ),
    sample_rate: Optional[int] = typer.Option(
        None, "--sample-rate", "-r", help="Target sample rate (Hz)"
    ),
    compression: Optional[int] = typer.Option(
        None, "--compression", help="FLAC compression level (0-12)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview processing without actually converting files"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed configuration"
    ),
    no_move: bool = typer.Option(
        False, "--no-move", help="Don't move processed files to input/processed/"
    ),
):
    """
    🎵 Process audio files with optimal FLAC conversion for transcription

    This command processes audio files in the input directory, applying
    optimal settings for speech transcription by LLMs. Files are converted
    to 16kHz mono FLAC with high compression for maximum size reduction
    while preserving speech quality.
    """
    # Load or create configuration
    if interactive:
        config = interactive_config()
    else:
        config = load_config(config_file)

        # Apply command-line overrides
        if format != OutputFormat.flac:
            config.output_format = format
        if sample_rate:
            config.target_sample_rate = sample_rate
        if compression is not None:
            config.flac_compression_level = compression
        if no_move:
            config.move_processed = False

    # Display header
    console.print("\n")
    console.print(
        Panel.fit(
            "🎧 [bold blue]Audio Splitter - Enhanced Edition[/bold blue]\n"
            "✨ Features: Optimal FLAC • Speech Transcription • LLM Ready\n"
            "🔧 Engine: Librosa + FFmpeg with intelligent processing",
            title="Audio Processing",
            border_style="blue",
        )
    )

    if verbose:
        show_config_table(config)

    # Check directories
    if not input_dir.exists():
        console.print(f"📁 Input directory {input_dir} does not exist. Creating it...")
        input_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"   ✓ Created directory: {input_dir}")
        console.print(
            f"\n📝 Please place your audio files in the '{input_dir}' directory and run again."
        )
        console.print(f"   Supported formats: MP3, WAV, M4A, FLAC, OGG, AAC, MP4")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # Dry run mode
    if dry_run:
        console.print(f"\n🔍 [bold yellow]DRY RUN MODE - Preview Only[/bold yellow]")

        # Scan files
        audio_extensions = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".mp4"}
        audio_files = [
            f
            for f in input_dir.iterdir()
            if f.is_file() and f.suffix.lower() in audio_extensions
        ]

        if not audio_files:
            console.print(f"   ❌ No audio files found in {input_dir}")
            return

        # Show files table
        table = Table(title="Files to Process")
        table.add_column("File", style="cyan")
        table.add_column("Size", style="green")
        table.add_column("Expected Output", style="yellow")

        total_size = 0
        for audio_file in audio_files:
            size_mb = audio_file.stat().st_size / (1024 * 1024)
            total_size += size_mb
            output_name = f"{audio_file.stem}_full_16k.{config.output_format.value}"
            table.add_row(audio_file.name, f"{size_mb:.1f}MB", output_name)

        table.add_row(
            "[bold]TOTAL[/bold]", f"[bold]{total_size:.1f}MB[/bold]", "", style="bold"
        )
        console.print(table)

        console.print(f"\n📊 [bold]Processing Configuration:[/bold]")
        console.print(f"   Target sample rate: {config.target_sample_rate.value} Hz")
        console.print(
            f"   FLAC compression: Level {config.flac_compression_level.value}"
        )
        console.print(f"   Output format: {config.output_format.value.upper()}")
        console.print(f"   Expected size reduction: ~90-95%")

        console.print(f"\n💡 Run without --dry-run to process files")
        return

    # Process files
    proc_config = config.to_processing_config()

    try:
        console.print(
            f"\n🚀 Starting processing with {config.output_format.upper()} optimization..."
        )

        process_audio_files(
            input_dir,
            output_dir,
            chunk_duration=proc_config["chunk_duration"],
            silence_threshold=proc_config["silence_threshold"],
            min_silence_duration=proc_config["min_silence_duration"],
            create_metadata=proc_config["create_metadata"],
            output_format=proc_config["output_format"],
            move_processed=config.move_processed,
        )

        console.print(
            f"\n✅ [bold green]Processing completed successfully![/bold green]"
        )
        console.print(f"📂 Output saved to: {output_dir}")

    except Exception as e:
        console.print(f"\n❌ [bold red]Error during processing:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def config(
    show: bool = typer.Option(
        False, "--show", help="Show current default configuration"
    ),
    create: bool = typer.Option(
        False, "--create", help="Create sample configuration file"
    ),
    edit: bool = typer.Option(False, "--edit", help="Edit configuration interactively"),
    file: Optional[Path] = typer.Option(
        None, "--file", "-f", help="Configuration file to show/edit"
    ),
):
    """
    ⚙️ Manage configuration settings

    Create, view, or edit configuration files for audio processing.
    """
    if create:
        config = AudioConfig()
        config_file = Path("audio_config.yaml")
        save_config(config, config_file)
        console.print(f"📄 Sample configuration created: {config_file}")
        console.print(f"   Edit this file to customize processing parameters")

    elif edit:
        if file and file.exists():
            config = load_config(file)
            console.print(f"📝 Editing configuration from: {file}")
        else:
            config = AudioConfig()

        updated_config = interactive_config()

        if file:
            save_config(updated_config, file)

    elif show:
        if file:
            config = load_config(file)
            console.print(f"📋 Configuration from: {file}")
        else:
            config = AudioConfig()
            console.print(f"📋 Default Configuration")

        show_config_table(config)

    else:
        console.print("💡 Use --show, --create, or --edit to manage configurations")
        console.print("   Example: audio-splitter config --create")


@app.command()
def optimize(
    input_file: Path = typer.Argument(..., help="Input audio file to optimize"),
    output_file: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file path"
    ),
    sample_rate: SampleRate = typer.Option(
        SampleRate.speech, "--sample-rate", "-r", help="Target sample rate"
    ),
    compression: CompressionLevel = typer.Option(
        CompressionLevel.high, "--compression", "-c", help="FLAC compression level"
    ),
):
    """
    ⚡ Convert single audio file to optimized FLAC for transcription

    Quickly convert a single audio file to the optimal format for
    speech transcription (16kHz, mono, FLAC with high compression).
    """
    if not input_file.exists():
        console.print(f"❌ Input file not found: {input_file}")
        raise typer.Exit(1)

    if output_file is None:
        output_file = input_file.parent / f"{input_file.stem}_optimized_16k.flac"

    console.print(f"\n⚡ [bold blue]Single File Optimization[/bold blue]")
    console.print(f"📁 Input: {input_file}")
    console.print(f"📁 Output: {output_file}")
    console.print(f"🎵 Settings: {sample_rate.value}Hz, FLAC Level {compression.value}")

    try:
        # Use the MultiFormatExporter directly
        exporter = MultiFormatExporter(
            target_sample_rate=sample_rate.value,
            flac_compression_level=compression.value,
        )

        console.print(f"\n🔄 Converting...")
        success = exporter.export_full_file_flac(input_file, output_file)

        if success:
            # Show size comparison
            original_size = input_file.stat().st_size / (1024 * 1024)
            optimized_size = output_file.stat().st_size / (1024 * 1024)
            reduction = (1 - optimized_size / original_size) * 100

            table = Table(title="Optimization Results")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Original Size", f"{original_size:.1f} MB")
            table.add_row("Optimized Size", f"{optimized_size:.1f} MB")
            table.add_row("Size Reduction", f"{reduction:.1f}%")
            table.add_row("Sample Rate", f"{sample_rate.value} Hz")
            table.add_row("Compression", f"FLAC Level {compression.value}")

            console.print(table)
            console.print(f"\n✅ [bold green]Optimization completed![/bold green]")
        else:
            console.print(f"❌ [bold red]Optimization failed[/bold red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"❌ [bold red]Error during optimization:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def analyze(
    input_file: Path = typer.Argument(..., help="Audio file to analyze"),
    show_silence: bool = typer.Option(
        True, "--silence/--no-silence", help="Show silence segments"
    ),
    threshold: float = typer.Option(
        0.01, "--threshold", "-t", help="Silence threshold"
    ),
    min_silence: float = typer.Option(
        25.0,
        "--min-silence",
        "-m",
        help="Minimum silence duration to create split (seconds)",
    ),
):
    """
    🔍 Analyze audio file properties and silence patterns

    Analyze an audio file to understand its characteristics and
    predict how it would be processed without actually converting it.
    """
    if not input_file.exists():
        console.print(f"❌ Input file not found: {input_file}")
        raise typer.Exit(1)

    console.print(f"\n🔍 [bold blue]Audio File Analysis[/bold blue]")
    console.print(f"📁 File: {input_file}")

    try:
        import librosa
        import numpy as np

        # Get basic file info
        file_size_mb = input_file.stat().st_size / (1024 * 1024)
        duration = librosa.get_duration(path=str(input_file))
        y, sr = librosa.load(str(input_file), sr=None)

        # Create info table
        table = Table(title="File Properties")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("File Size", f"{file_size_mb:.1f} MB")
        table.add_row("Duration", f"{duration / 60:.1f} minutes")
        table.add_row("Sample Rate", f"{sr} Hz")
        table.add_row("Channels", "Mono" if len(y.shape) == 1 else "Stereo")
        table.add_row("Samples", f"{len(y):,}")

        console.print(table)

        if show_silence:
            console.print(f"\n🔇 [bold cyan]Silence Analysis[/bold cyan]")
            console.print(f"   Threshold: {threshold}")
            console.print(f"   Min duration for split: {min_silence}s")

            # Simple silence detection for analysis
            rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
            silence_mask = rms < threshold

            if silence_mask.any():
                silence_percentage = (silence_mask.sum() / len(silence_mask)) * 100
                console.print(f"   Silence detected: {silence_percentage:.1f}% of file")

                # Find silence segments
                silence_diff = np.diff(
                    np.concatenate(([False], silence_mask, [False])).astype(int)
                )
                silence_starts = np.where(silence_diff == 1)[0]
                silence_ends = np.where(silence_diff == -1)[0]

                console.print(f"   Silence segments: {len(silence_starts)}")

                long_silence_count = 0
                for start, end in zip(silence_starts, silence_ends):
                    duration_frames = end - start
                    duration_seconds = duration_frames * (len(y) / len(rms)) / sr
                    if duration_seconds >= min_silence:
                        long_silence_count += 1

                console.print(f"   Segments ≥{min_silence}s: {long_silence_count}")

                if long_silence_count > 0:
                    console.print(
                        f"   [green]✓ File would be split into {long_silence_count + 1} chunks[/green]"
                    )
                else:
                    console.print(
                        f"   [yellow]! File would not be split (no {min_silence}s+ silence)[/yellow]"
                    )
            else:
                console.print(
                    f"   [yellow]No silence detected at threshold {threshold}[/yellow]"
                )

        # Optimization prediction
        console.print(f"\n📊 [bold cyan]Optimization Prediction[/bold cyan]")
        channels = 1 if len(y.shape) == 1 else 2
        expected_reduction = 50 if channels == 2 else 0  # Mono conversion
        if sr > 16000:
            expected_reduction += 60  # Sample rate reduction
        expected_reduction += 30  # FLAC compression
        expected_reduction = min(expected_reduction, 95)  # Cap at 95%

        optimized_size = file_size_mb * (1 - expected_reduction / 100)

        console.print(
            f"   Current: {file_size_mb:.1f} MB → Optimized: ~{optimized_size:.1f} MB"
        )
        console.print(f"   Expected reduction: ~{expected_reduction}%")

    except Exception as e:
        console.print(f"❌ [bold red]Error during analysis:[/bold red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

