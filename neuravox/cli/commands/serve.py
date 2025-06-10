"""CLI command for running the API server"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from neuravox.api.main import run_server

console = Console()


def serve_command(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", help="Port to bind to"),
    workers: int = typer.Option(1, "--workers", help="Number of worker processes"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Configuration file path")
):
    """Start the Neuravox API server"""
    
    console.print(f"[bold green]Starting Neuravox API server[/bold green]")
    console.print(f"Host: {host}")
    console.print(f"Port: {port}")
    console.print(f"Workers: {workers}")
    console.print(f"Reload: {reload}")
    if config_path:
        console.print(f"Config: {config_path}")
    
    console.print(f"\n[dim]API will be available at: http://{host}:{port}/api/docs[/dim]")
    console.print(f"[dim]Health check: http://{host}:{port}/api/v1/health[/dim]\n")
    
    try:
        run_server(
            host=host,
            port=port,
            workers=workers,
            reload=reload,
            config_path=config_path
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Server failed to start: {e}[/red]")
        raise typer.Exit(1)