import typer
from typing import Optional, List
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text
import asyncio

from .config import config_manager, ProjectConfig
from .transcriber import AudioTranscriber

app = typer.Typer(
    name="audio-transcriber",
    help="CLI tool for transcribing audio files using various AI models",
    rich_markup_mode="rich"
)
console = Console()


@app.command()
def interactive():
    """Start interactive mode for audio transcription."""
    console.print("\n[bold blue]🎵 Audio Transcriber[/bold blue]", justify="center")
    console.print("[dim]Interactive Mode[/dim]\n", justify="center")
    
    try:
        # Load configuration
        config = config_manager.config
        
        # Step 1: Select model
        model_key = select_model()
        if not model_key:
            console.print("[red]No model selected. Exiting.[/red]")
            return
        
        # Step 2: Select audio files
        audio_files = select_audio_files()
        if not audio_files:
            console.print("[red]No audio files selected. Exiting.[/red]")
            return
        
        # Step 3: Configure project
        project_name = get_project_name(audio_files[0] if len(audio_files) == 1 else "batch_transcription")
        
        # Create project configuration
        project = ProjectConfig(
            name=project_name,
            output_dir=config.output_dir / project_name,
            model=model_key,
            audio_files=audio_files
        )
        
        # Step 4: Confirm and transcribe
        show_project_summary(project, model_key)
        
        if Confirm.ask("\n[bold]Start transcription?[/bold]"):
            asyncio.run(run_transcription(project))
        else:
            console.print("[yellow]Transcription cancelled.[/yellow]")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")


@app.command()
def transcribe(
    audio_file: Path = typer.Argument(..., help="Audio file to transcribe"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use for transcription"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    project_name: Optional[str] = typer.Option(None, "--project", "-p", help="Project name")
):
    """Transcribe a single audio file."""
    try:
        # Validate audio file
        if not audio_file.exists():
            console.print(f"[red]Error: Audio file not found: {audio_file}[/red]")
            raise typer.Exit(1)
        
        # Get model
        config = config_manager.config
        model_key = model or config.default_model
        
        if model_key not in config.models:
            console.print(f"[red]Error: Model '{model_key}' not found.[/red]")
            list_models()
            raise typer.Exit(1)
        
        # Create project
        project_name = project_name or audio_file.stem
        project = ProjectConfig(
            name=project_name,
            output_dir=config.output_dir / project_name,
            model=model_key,
            audio_files=[audio_file]
        )
        
        # Run transcription
        asyncio.run(run_transcription(project))
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list_models():
    """List available transcription models."""
    config = config_manager.config
    
    if not config.models:
        console.print("[yellow]No models configured.[/yellow]")
        return
    
    table = Table(title="Available Models")
    table.add_column("Key", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Provider", style="blue")
    table.add_column("Model ID", style="magenta")
    table.add_column("Available", style="yellow")
    
    for key, model_config in config.models.items():
        available = "✓" if model_config.api_key or model_config.provider == "ollama" else "✗"
        table.add_row(
            key,
            model_config.name,
            model_config.provider,
            model_config.model_id,
            available
        )
    
    console.print(table)


@app.command()
def list_audio():
    """List available audio files in the input directory."""
    config = config_manager.config
    input_dir = config.input_dir
    
    if not input_dir.exists():
        console.print(f"[yellow]Input directory does not exist: {input_dir}[/yellow]")
        return
    
    audio_extensions = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma"}
    audio_files = [
        f for f in input_dir.rglob("*")
        if f.is_file() and f.suffix.lower() in audio_extensions
    ]
    
    if not audio_files:
        console.print(f"[yellow]No audio files found in {input_dir}[/yellow]")
        return
    
    table = Table(title=f"Audio Files in {input_dir}")
    table.add_column("File", style="cyan")
    table.add_column("Size", style="green")
    table.add_column("Modified", style="blue")
    
    for audio_file in sorted(audio_files):
        size = audio_file.stat().st_size
        size_str = f"{size / (1024*1024):.1f} MB" if size > 1024*1024 else f"{size / 1024:.1f} KB"
        modified = audio_file.stat().st_mtime
        import datetime
        modified_str = datetime.datetime.fromtimestamp(modified).strftime("%Y-%m-%d %H:%M")
        
        table.add_row(
            str(audio_file.relative_to(input_dir)),
            size_str,
            modified_str
        )
    
    console.print(table)


def select_model() -> Optional[str]:
    """Interactive model selection."""
    config = config_manager.config
    
    if not config.models:
        console.print("[red]No models configured. Please check your configuration.[/red]")
        return None
    
    console.print("[bold]Available Models:[/bold]")
    
    # Create model choices
    model_choices = []
    for i, (key, model_config) in enumerate(config.models.items(), 1):
        available = "✓" if model_config.api_key or model_config.provider == "ollama" else "✗"
        status_color = "green" if available == "✓" else "red"
        
        console.print(f"  {i}. [{status_color}]{available}[/{status_color}] {model_config.name} ({key})")
        model_choices.append(key)
    
    while True:
        try:
            choice = Prompt.ask(
                f"\nSelect model [1-{len(model_choices)}]",
                default="1"
            )
            index = int(choice) - 1
            if 0 <= index < len(model_choices):
                return model_choices[index]
            else:
                console.print(f"[red]Please enter a number between 1 and {len(model_choices)}[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number[/red]")


def select_audio_files() -> List[Path]:
    """Interactive audio file selection."""
    config = config_manager.config
    input_dir = config.input_dir
    
    if not input_dir.exists():
        console.print(f"[red]Input directory does not exist: {input_dir}[/red]")
        return []
    
    audio_extensions = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma"}
    audio_files = [
        f for f in input_dir.rglob("*")
        if f.is_file() and f.suffix.lower() in audio_extensions
    ]
    
    if not audio_files:
        console.print(f"[red]No audio files found in {input_dir}[/red]")
        return []
    
    console.print(f"\n[bold]Audio files in {input_dir}:[/bold]")
    
    for i, audio_file in enumerate(audio_files, 1):
        rel_path = audio_file.relative_to(input_dir)
        console.print(f"  {i}. {rel_path}")
    
    console.print(f"  {len(audio_files) + 1}. All files")
    
    while True:
        try:
            choice = Prompt.ask(
                f"\nSelect files [1-{len(audio_files) + 1}, or comma-separated list]",
                default="1"
            )
            
            if choice.strip() == str(len(audio_files) + 1):
                return audio_files
            
            # Parse comma-separated choices
            choices = [int(c.strip()) for c in choice.split(",")]
            selected_files = []
            
            for c in choices:
                if 1 <= c <= len(audio_files):
                    selected_files.append(audio_files[c - 1])
                else:
                    console.print(f"[red]Invalid choice: {c}[/red]")
                    break
            else:
                return selected_files
                
        except ValueError:
            console.print("[red]Please enter valid numbers[/red]")


def get_project_name(default_name: str) -> str:
    """Get project name from user."""
    project_name = Prompt.ask(
        "\n[bold]Project name[/bold]",
        default=default_name
    )
    return project_name.strip()


def show_project_summary(project: ProjectConfig, model_key: str):
    """Display project summary before transcription."""
    config = config_manager.config
    model_config = config.models[model_key]
    
    summary_text = Text()
    summary_text.append("Project: ", style="bold")
    summary_text.append(f"{project.name}\n", style="cyan")
    summary_text.append("Model: ", style="bold")
    summary_text.append(f"{model_config.name} ({model_key})\n", style="green")
    summary_text.append("Files: ", style="bold")
    summary_text.append(f"{len(project.audio_files)} audio file(s)\n", style="yellow")
    summary_text.append("Output: ", style="bold")
    summary_text.append(str(project.output_dir), style="blue")
    
    panel = Panel(summary_text, title="[bold]Transcription Summary[/bold]", border_style="blue")
    console.print(panel)


async def run_transcription(project: ProjectConfig):
    """Run the transcription process."""
    try:
        # Create transcriber
        transcriber = AudioTranscriber()
        
        # Track if any transcription succeeds
        has_success = False
        
        # Run transcription with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            for i, audio_file in enumerate(project.audio_files):
                task_id = progress.add_task(
                    f"Transcribing {audio_file.name} ({i+1}/{len(project.audio_files)})...",
                    total=None
                )
                
                try:
                    result = await transcriber.transcribe_file(
                        audio_file, 
                        project.model, 
                        project.output_dir
                    )
                    
                    # Save project config only on first success
                    if not has_success:
                        config_manager.save_project_config(project)
                        has_success = True
                    
                    progress.update(task_id, description=f"✓ Completed {audio_file.name}")
                    console.print(f"[green]✓ {audio_file.name} -> {result['output_file']}[/green]")
                    
                except Exception as e:
                    progress.update(task_id, description=f"✗ Failed {audio_file.name}")
                    console.print(f"[red]✗ {audio_file.name}: {e}[/red]")
        
        # Only update recent projects if we had at least one success
        if has_success:
            config_manager.config.add_recent_project(project.name)
            config_manager.save_config()
        
        console.print(f"\n[bold green]Transcription completed![/bold green]")
        console.print(f"Results saved to: [blue]{project.output_dir}[/blue]")
        
    except Exception as e:
        console.print(f"[red]Transcription failed: {e}[/red]")
        raise


if __name__ == "__main__":
    app()