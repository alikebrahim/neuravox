"""Workspace management commands"""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel

from neuravox.cli.utils import load_config
from neuravox.cli.display import ResultDisplay
from neuravox.core.state_manager import StateManager
from neuravox.shared.file_utils import get_audio_files


def init_command(
    workspace: Optional[Path] = typer.Option(
        None, "--workspace", "-w", help="Workspace directory path"
    ),
    console: Console = Console()
):
    """Initialize workspace directories"""
    config = load_config()

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
            title="Workspace Initialization",
        )
    )


def status_command(
    workspace: Optional[Path] = typer.Option(
        None, "--workspace", "-w", help="Workspace directory path"
    ),
    console: Console = Console()
):
    """Show workspace and pipeline status"""
    config = load_config()
    
    if workspace:
        config.workspace = Path(workspace).expanduser()

    # Check if workspace exists
    if not config.workspace.exists():
        console.print("[red]Workspace not found. Run 'neuravox init' first.[/red]")
        raise typer.Exit(1)

    # Get file counts
    input_files = get_audio_files(config.input_path)
    processed_files = get_audio_files(config.processed_path)
    transcribed_files = get_audio_files(config.transcribed_path)

    # Show workspace info
    ResultDisplay.show_config_info(config, console)
    
    # Show file counts
    console.print("\n[bold blue]File Status:[/bold blue]")
    console.print(f"  Input files: {len(input_files)}")
    console.print(f"  Processed files: {len(processed_files)}")
    console.print(f"  Transcribed files: {len(transcribed_files)}")

    # Show pipeline status if available
    try:
        state_manager = StateManager(config.workspace)
        summary = state_manager.get_pipeline_summary()
        
        if summary and summary.get('total_files', 0) > 0:
            console.print("\n[bold blue]Pipeline Status:[/bold blue]")
            for stage, count in summary.get('stage_counts', {}).items():
                console.print(f"  {stage.title()}: {count}")
    except Exception:
        # Pipeline status not available
        pass


def resume_command(
    workspace: Optional[Path] = typer.Option(
        None, "--workspace", "-w", help="Workspace directory path"
    ),
    console: Console = Console()
):
    """Resume interrupted pipeline processing"""
    config = load_config()
    
    if workspace:
        config.workspace = Path(workspace).expanduser()

    if not config.workspace.exists():
        console.print("[red]Workspace not found. Run 'neuravox init' first.[/red]")
        raise typer.Exit(1)

    try:
        state_manager = StateManager(config.workspace)
        summary = state_manager.get_pipeline_summary()
        
        if not summary or summary.get('total_files', 0) == 0:
            console.print("[yellow]No pipeline state found. Nothing to resume.[/yellow]")
            raise typer.Exit(0)
        
        # Show what will be resumed
        console.print("[bold blue]Pipeline State:[/bold blue]")
        for stage, count in summary.get('stage_counts', {}).items():
            console.print(f"  {stage.title()}: {count}")
        
        # Import here to avoid circular imports
        from neuravox.core.pipeline import AudioPipeline
        
        pipeline = AudioPipeline(config)
        
        console.print("\n[yellow]Resuming pipeline processing...[/yellow]")
        pipeline.resume()
        
        console.print("[green]✓ Pipeline resumed successfully[/green]")
        
    except Exception as e:
        console.print(f"[red]Failed to resume pipeline: {e}[/red]")
        raise typer.Exit(1)