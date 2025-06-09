"""
Unified CLI for Neuravox platform
"""
import typer
from pathlib import Path
from typing import List, Optional, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text
import asyncio
import sys

from neuravox.core.pipeline import AudioPipeline
from neuravox.shared.config import UnifiedConfig
from neuravox.shared.file_utils import get_audio_files, format_file_size, format_duration

app = typer.Typer(
    name="neuravox",
    help="Neuravox - Neural audio processing and transcription platform",
    rich_markup_mode="rich"
)
console = Console()

@app.command()
def init(
    workspace: Optional[Path] = typer.Option(None, "--workspace", "-w", 
                                            help="Workspace directory path")
):
    """Initialize workspace and configuration"""
    config = UnifiedConfig()
    
    if workspace:
        config.workspace.base_path = workspace
    
    # Create directories
    directories = [
        config.workspace.input_path,
        config.workspace.processed_path,
        config.workspace.transcribed_path
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Save configuration
    config_path = config.workspace.base_path / "config.yaml"
    config.save(config_path)
    
    console.print(Panel(
        f"[green]✓ Workspace initialized at {config.workspace.base_path}[/green]\n\n"
        f"Directories created:\n"
        f"  • Input: {config.workspace.input_path}\n"
        f"  • Processed: {config.workspace.processed_path}\n"
        f"  • Transcribed: {config.workspace.transcribed_path}\n\n"
        f"Configuration saved to: {config_path}",
        title="Workspace Initialized",
        border_style="green"
    ))

@app.command()
def process(
    files: Optional[List[Path]] = typer.Argument(None, help="Audio files to process"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Transcription model"),
    interactive: bool = typer.Option(False, "--interactive", "-i", 
                                   help="Interactive file selection"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", 
                                              help="Configuration file path")
):
    """Process audio files through full pipeline"""
    # Load configuration
    config = UnifiedConfig(config_path) if config_path else UnifiedConfig()
    
    # Validate API keys are configured
    model_to_use = model or config.transcription.default_model
    if model_to_use.startswith("google") and not config.api_keys.google_api_key:
        console.print("[red]Error: Google API key not configured[/red]")
        console.print("Set GOOGLE_API_KEY environment variable or add to config")
        raise typer.Exit(1)
    elif model_to_use.startswith("openai") and not config.api_keys.openai_api_key:
        console.print("[red]Error: OpenAI API key not configured[/red]")
        console.print("Set OPENAI_API_KEY environment variable or add to config")
        raise typer.Exit(1)
    
    pipeline = AudioPipeline(config)
    
    # Get files to process
    if interactive or not files:
        files = _interactive_file_selection(config)
        if not files:
            return
    
    # Validate all files exist and are audio files
    valid_files = []
    for file in files:
        if not file.exists():
            console.print(f"[red]File not found: {file}[/red]")
            continue
        if not file.is_file():
            console.print(f"[red]Not a file: {file}[/red]")
            continue
        if file.suffix.lower() not in {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.opus', '.wma', '.aac', '.mp4'}:
            console.print(f"[red]Unsupported format: {file.suffix} ({file.name})[/red]")
            continue
        valid_files.append(file)
    
    if not valid_files:
        console.print("[red]No valid audio files to process[/red]")
        return
    
    files = valid_files
    
    # Show processing plan
    console.print(f"\n[bold]Processing {len(files)} file(s)[/bold]")
    console.print(f"Model: {model or config.transcription.default_model}")
    console.print(f"Workspace: {config.workspace.base_path}\n")
    
    if not Confirm.ask("Continue with processing?"):
        console.print("[yellow]Processing cancelled[/yellow]")
        return
    
    # Process files
    async def run_pipeline():
        with console.status("[bold blue]Processing audio files...") as status:
            results = await pipeline.process_batch(files, model)
            
        # Show results
        _display_results(results)
    
    asyncio.run(run_pipeline())

@app.command()
def status(
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", 
                                              help="Configuration file path")
):
    """Show pipeline status and recent activity"""
    config = UnifiedConfig(config_path) if config_path else UnifiedConfig()
    pipeline = AudioPipeline(config)
    
    summary = pipeline.get_status()
    
    # Display status counts
    console.print(Panel(
        f"[bold]Pipeline Status[/bold]\n\n"
        f"Total files: {summary['total_files']}\n"
        f"Completed: {summary['status_counts'].get('completed', 0)}\n"
        f"Processing: {summary['status_counts'].get('processing', 0)}\n"
        f"Failed: {summary['status_counts'].get('failed', 0)}",
        title="Status Summary",
        border_style="blue"
    ))
    
    # Display recent activity
    if summary['recent_activity']:
        table = Table(title="Recent Activity")
        table.add_column("File ID", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Updated", style="green")
        
        for activity in summary['recent_activity']:
            table.add_row(
                activity['file_id'],
                activity['status'],
                activity['updated_at']
            )
        
        console.print(table)

@app.command()
def resume(
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Transcription model"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", 
                                              help="Configuration file path")
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
            file_info['file_id'],
            Path(file_info['original_path']).name,
            file_info.get('error_message', 'Unknown error')[:50] + "..."
        )
    
    console.print(table)
    
    if Confirm.ask(f"\nResume processing {len(failed_files)} failed file(s)?"):
        files = [Path(f['original_path']) for f in failed_files]
        
        async def run_resume():
            results = await pipeline.process_batch(files, model)
            _display_results(results)
        
        asyncio.run(run_resume())

@app.command()
def config(
    show: bool = typer.Option(False, "--show", "-s", help="Show current configuration"),
    edit: bool = typer.Option(False, "--edit", "-e", help="Edit configuration"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", 
                                              help="Configuration file path")
):
    """Manage configuration"""
    config = UnifiedConfig(config_path) if config_path else UnifiedConfig()
    
    if show:
        # Display current configuration
        console.print(Panel(
            f"[bold]Current Configuration[/bold]\n\n"
            f"[yellow]Workspace:[/yellow]\n"
            f"  Base path: {config.workspace.base_path}\n"
            f"  Input: {config.workspace.input_dir}\n"
            f"  Processed: {config.workspace.processed_dir}\n"
            f"  Transcribed: {config.workspace.transcribed_dir}\n\n"
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
            border_style="blue"
        ))
    
    elif edit:
        # Interactive configuration editing
        console.print("[yellow]Configuration editing not yet implemented[/yellow]")
        console.print("Please edit the configuration file directly:")
        console.print(f"  {config.config_path}")

def _interactive_file_selection(config: UnifiedConfig) -> List[Path]:
    """Interactive file selection from input directory"""
    audio_files = get_audio_files(config.workspace.input_path)
    
    if not audio_files:
        console.print(f"[yellow]No audio files found in {config.workspace.input_path}[/yellow]")
        return []
    
    # Display available files
    table = Table(title="Available Audio Files")
    table.add_column("Index", style="cyan", width=6)
    table.add_column("File Name", style="magenta")
    table.add_column("Size", style="green", width=10)
    
    for i, file in enumerate(audio_files):
        size = format_file_size(file.stat().st_size)
        table.add_row(str(i), file.name, size)
    
    console.print(table)
    
    # Get selection
    selection = Prompt.ask(
        "\nSelect files to process (comma-separated indices, ranges like 0-2, or 'all')",
        default="all"
    )
    
    if selection.lower() == 'all':
        return audio_files
    
    # Parse selection
    selected_indices = []
    for part in selection.split(','):
        part = part.strip()
        if '-' in part:
            # Range
            start, end = part.split('-')
            selected_indices.extend(range(int(start), int(end) + 1))
        else:
            # Single index
            selected_indices.append(int(part))
    
    # Get selected files
    selected_files = []
    for i in selected_indices:
        if 0 <= i < len(audio_files):
            selected_files.append(audio_files[i])
    
    return selected_files

def _display_results(results: List[Dict[str, Any]]):
    """Display processing results"""
    success_count = sum(1 for r in results if r['status'] == 'completed')
    failed_count = sum(1 for r in results if r['status'] == 'failed')
    
    # Summary
    console.print(Panel(
        f"[bold]Processing Complete[/bold]\n\n"
        f"Total files: {len(results)}\n"
        f"[green]Successful: {success_count}[/green]\n"
        f"[red]Failed: {failed_count}[/red]",
        title="Results Summary",
        border_style="blue" if failed_count == 0 else "yellow"
    ))
    
    # Details table
    if results:
        table = Table(title="Processing Details")
        table.add_column("File", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Time", style="green")
        table.add_column("Details", style="yellow")
        
        for result in results:
            status_style = "green" if result['status'] == 'completed' else "red"
            time_str = f"{result.get('total_time', 0):.1f}s" if 'total_time' in result else "N/A"
            
            details = ""
            if result['status'] == 'completed' and result.get('transcription_result'):
                chunks = result['transcription_result'].get('chunks', 0)
                details = f"{chunks} chunks transcribed"
            elif result['status'] == 'failed':
                details = result.get('error', 'Unknown error')[:40] + "..."
            
            table.add_row(
                result['file_id'],
                f"[{status_style}]{result['status']}[/{status_style}]",
                time_str,
                details
            )
        
        console.print(table)

if __name__ == "__main__":
    app()