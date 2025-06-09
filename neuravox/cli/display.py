"""Display utilities for CLI commands"""

from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pathlib import Path

from neuravox.shared.file_utils import format_file_size


class ResultDisplay:
    """Handles formatting and display of command results"""
    
    @staticmethod
    def show_operation_results(
        results: List[Dict[str, Any]], 
        operation_type: str,
        console: Console
    ):
        """Display results from processing operations"""
        if not results:
            return
        
        # Create table for results
        table = Table(title=f"{operation_type.title()} Results")
        table.add_column("File", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="white")
        
        success_count = 0
        failed_count = 0
        
        for result in results:
            if isinstance(result, dict):
                if result.get("status") == "success":
                    success_count += 1
                    status = "[green]✓ Success[/green]"
                    
                    # Format details based on operation type
                    if operation_type == "conversion":
                        details = f"Format: {result.get('format', 'N/A')}"
                        if result.get('compression_ratio'):
                            details += f" | Ratio: {result['compression_ratio']:.2f}"
                    elif operation_type == "processing":
                        chunk_count = len(result.get('chunks', []))
                        details = f"Chunks: {chunk_count}"
                    elif operation_type == "transcription":
                        details = f"Duration: {result.get('duration', 'N/A')}s"
                    else:
                        details = "Completed"
                        
                else:
                    failed_count += 1
                    status = "[red]✗ Failed[/red]"
                    details = result.get("error", "Unknown error")
                
                filename = Path(result.get("input_file", "Unknown")).name
                table.add_row(filename, status, details)
        
        console.print(table)
        ResultDisplay.show_summary_panel(success_count, failed_count, operation_type, console)
    
    @staticmethod
    def show_summary_panel(
        success_count: int, 
        failed_count: int, 
        operation_type: str,
        console: Console
    ):
        """Display summary panel with operation statistics"""
        total = success_count + failed_count
        
        if failed_count == 0:
            color = "green"
            status_text = "All operations completed successfully!"
        elif success_count == 0:
            color = "red"
            status_text = "All operations failed!"
        else:
            color = "yellow"
            status_text = "Some operations failed."
        
        summary = (
            f"[{color}]{status_text}[/{color}]\n\n"
            f"Total files: {total}\n"
            f"Successful: {success_count}\n"
            f"Failed: {failed_count}"
        )
        
        console.print(Panel(summary, title=f"{operation_type.title()} Summary"))
    
    @staticmethod
    def show_file_list(files: List[Path], title: str, console: Console):
        """Display a formatted list of files"""
        if not files:
            console.print(f"[yellow]No files found for {title.lower()}[/yellow]")
            return
        
        table = Table(title=title)
        table.add_column("File", style="cyan")
        table.add_column("Size", style="white")
        
        for file_path in files:
            size = format_file_size(file_path.stat().st_size)
            table.add_row(file_path.name, size)
        
        console.print(table)
    
    @staticmethod
    def show_config_info(config: Any, console: Console):
        """Display current configuration information"""
        table = Table(title="Current Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")
        
        # Add configuration details based on type
        if hasattr(config, 'workspace'):
            table.add_row("Workspace", str(config.workspace))
        
        if hasattr(config, 'processing'):
            table.add_row("Silence Threshold", str(config.processing.silence_threshold))
            table.add_row("Sample Rate", str(config.processing.sample_rate))
            table.add_row("Output Format", config.processing.output_format)
        
        if hasattr(config, 'transcription'):
            table.add_row("Default Model", config.transcription.default_model)
            table.add_row("Max Concurrent", str(config.transcription.max_concurrent))
        
        console.print(table)