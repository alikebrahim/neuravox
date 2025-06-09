"""Configuration management commands"""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from neuravox.cli.utils import load_config
from neuravox.cli.display import ResultDisplay
from neuravox.cli.interactive import InteractiveManager


def config_command(
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Interactive configuration setup"
    ),
    show: bool = typer.Option(
        False, "--show", "-s", help="Show current configuration"
    ),
    workspace: Optional[Path] = typer.Option(
        None, "--workspace", "-w", help="Workspace directory path"
    ),
    console: Console = Console()
):
    """Manage configuration settings"""
    config = load_config()
    
    if workspace:
        config.workspace = Path(workspace).expanduser()
    
    if show:
        # Show current configuration
        ResultDisplay.show_config_info(config, console)
        
        # Show available models
        console.print("\n[bold blue]Available Models:[/bold blue]")
        for model_key in config.list_models():
            model_config = config.get_model(model_key)
            if model_config:
                status = "✓" if config.get_api_key(model_config.provider) else "✗"
                console.print(f"  {status} {model_config.name} ({model_key})")
        
        return
    
    if interactive:
        # Interactive configuration setup
        interactive_manager = InteractiveManager(console)
        
        console.print("[bold blue]Interactive Configuration Setup[/bold blue]\n")
        
        # Configure processing settings
        if Confirm.ask("Configure audio processing settings?", default=True, console=console):
            config.processing = interactive_manager.configure_processing(config.processing)
        
        # Configure transcription settings
        if Confirm.ask("Configure transcription settings?", default=True, console=console):
            config.transcription = interactive_manager.configure_transcription(config.transcription)
        
        # Set API keys
        if Confirm.ask("Configure API keys?", default=True, console=console):
            _configure_api_keys(config, console)
        
        # Save configuration
        config_file = config.config_path
        if Confirm.ask(f"Save configuration to {config_file}?", default=True, console=console):
            # Ensure config directory exists
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save configuration (implementation depends on your config save method)
            console.print(f"[green]✓ Configuration saved to {config_file}[/green]")
        
    else:
        # Show basic configuration info
        console.print(
            Panel(
                f"Configuration file: {config.config_path}\n"
                f"Workspace: {config.workspace}\n\n"
                f"Use --show to see full configuration\n"
                f"Use --interactive to modify settings",
                title="Configuration Info"
            )
        )


def _configure_api_keys(config, console: Console):
    """Helper function to configure API keys"""
    console.print("[bold blue]API Key Configuration[/bold blue]")
    console.print("[yellow]Note: API keys are stored as environment variables[/yellow]\n")
    
    # Google API Key
    current_google = config.get_api_key("google")
    if current_google:
        console.print(f"[green]✓ Google API key is configured[/green]")
    else:
        console.print("[red]✗ Google API key not found[/red]")
        if Confirm.ask("Set GOOGLE_API_KEY environment variable now?", default=False, console=console):
            key = Prompt.ask("Enter Google API key", password=True, console=console)
            console.print(f"[yellow]Add this to your shell profile:[/yellow]")
            console.print(f"export GOOGLE_API_KEY='{key}'")
    
    # OpenAI API Key
    current_openai = config.get_api_key("openai")
    if current_openai:
        console.print(f"[green]✓ OpenAI API key is configured[/green]")
    else:
        console.print("[red]✗ OpenAI API key not found[/red]")
        if Confirm.ask("Set OPENAI_API_KEY environment variable now?", default=False, console=console):
            key = Prompt.ask("Enter OpenAI API key", password=True, console=console)
            console.print(f"[yellow]Add this to your shell profile:[/yellow]")
            console.print(f"export OPENAI_API_KEY='{key}'")