"""
Unified progress tracking for both audio processing and transcription
"""
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn, TimeElapsedColumn
from rich.console import Console
from typing import Optional, Dict, Any
import time

class UnifiedProgressTracker:
    """Unified progress tracking for both modules"""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            TimeElapsedColumn(),
            console=self.console
        )
        self.tasks: Dict[str, Any] = {}
        self.start_time = time.time()
    
    def add_task(self, name: str, description: str, total: int) -> str:
        """Add a new task to track"""
        task_id = self.progress.add_task(description, total=total)
        self.tasks[name] = {
            'id': task_id,
            'start_time': time.time(),
            'completed': 0,
            'total': total
        }
        return task_id
    
    def update_task(self, name: str, advance: int = 1, description: Optional[str] = None):
        """Update task progress"""
        if name in self.tasks:
            task_id = self.tasks[name]['id']
            self.progress.update(task_id, advance=advance)
            if description:
                self.progress.update(task_id, description=description)
            self.tasks[name]['completed'] += advance
    
    def finish_task(self, name: str):
        """Mark task as complete"""
        if name in self.tasks:
            task_id = self.tasks[name]['id']
            remaining = self.tasks[name]['total'] - self.tasks[name]['completed']
            if remaining > 0:
                self.progress.update(task_id, advance=remaining)
    
    def get_elapsed_time(self) -> float:
        """Get total elapsed time"""
        return time.time() - self.start_time
    
    def __enter__(self):
        self.progress.__enter__()
        return self
    
    def __exit__(self, *args):
        self.progress.__exit__(*args)


