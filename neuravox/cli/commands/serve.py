"""CLI command for running the API server"""

from pathlib import Path
from typing import Optional

import typer

from neuravox.api.main import run_server
from neuravox.shared.logging_config import get_cli_logger


def serve_command(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", help="Port to bind to"),
    workers: int = typer.Option(1, "--workers", help="Number of worker processes"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Configuration file path")
):
    """Start the Neuravox API server"""
    logger = get_cli_logger()
    
    # Structured startup logging
    logger.info("Starting Neuravox API server")
    logger.info(f"Configuration: host={host} port={port} workers={workers} reload={reload}")
    
    if config_path:
        logger.info(f"Using config file: {config_path}")
    
    logger.info(f"API documentation: http://{host}:{port}/api/docs")
    logger.info(f"Health check: http://{host}:{port}/api/v1/health")
    
    try:
        run_server(
            host=host,
            port=port,
            workers=workers,
            reload=reload,
            config_path=config_path
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        raise typer.Exit(1)