"""Health check and system status endpoints"""

import os
import psutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from neuravox.db.database import get_db_session
from neuravox.shared.config import UnifiedConfig
from neuravox.api.models.responses import HealthResponse


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db_session)):
    """Health check endpoint"""
    
    # Check database connectivity
    database_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        database_status = f"error: {str(e)}"
    
    # Check workspace accessibility
    config = UnifiedConfig()
    workspace_status = "healthy"
    try:
        if not config.workspace.exists():
            workspace_status = "workspace_not_found"
        elif not os.access(config.workspace, os.R_OK | os.W_OK):
            workspace_status = "workspace_not_accessible"
    except Exception as e:
        workspace_status = f"error: {str(e)}"
    
    # Check dependencies
    dependencies = {
        "ffmpeg": check_ffmpeg_availability(),
        "storage_space": check_storage_space(config.workspace),
        "memory_usage": f"{psutil.virtual_memory().percent}%",
        "cpu_usage": f"{psutil.cpu_percent(interval=1)}%"
    }
    
    # Determine overall status
    overall_status = "healthy"
    if database_status != "healthy" or workspace_status != "healthy":
        overall_status = "degraded"
    
    if "error" in database_status or "error" in workspace_status:
        overall_status = "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        version="1.0.0",
        timestamp=datetime.utcnow(),
        database=database_status,
        workspace=workspace_status,
        dependencies=dependencies
    )


@router.get("/status")
async def system_status():
    """Detailed system status endpoint"""
    
    config = UnifiedConfig()
    
    # System information
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(config.workspace)
    
    status = {
        "system": {
            "cpu_count": psutil.cpu_count(),
            "cpu_usage_percent": psutil.cpu_percent(interval=1),
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_usage_percent": memory.percent,
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_usage_percent": round((disk.used / disk.total) * 100, 2)
        },
        "workspace": {
            "path": str(config.workspace),
            "input_path": str(config.input_path),
            "processed_path": str(config.processed_path),
            "transcribed_path": str(config.transcribed_path),
            "input_files_count": count_files(config.input_path),
            "processed_files_count": count_files(config.processed_path),
            "transcribed_files_count": count_files(config.transcribed_path)
        },
        "configuration": {
            "processing": {
                "silence_threshold": config.processing.silence_threshold,
                "min_silence_duration": config.processing.min_silence_duration,
                "output_format": config.processing.output_format,
                "sample_rate": config.processing.sample_rate
            },
            "transcription": {
                "default_model": config.transcription.default_model,
                "max_concurrent": config.transcription.max_concurrent,
                "chunk_processing": config.transcription.chunk_processing
            },
            "available_models": list(config.models.keys())
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return status


def check_ffmpeg_availability() -> str:
    """Check if FFmpeg is available"""
    try:
        import subprocess
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Extract version from first line
            first_line = result.stdout.split('\n')[0]
            if "ffmpeg version" in first_line:
                return first_line.split()[2]
        return "unavailable"
    except Exception:
        return "unavailable"


def check_storage_space(path: Path) -> str:
    """Check available storage space"""
    try:
        disk = psutil.disk_usage(path)
        free_gb = disk.free / (1024**3)
        return f"{free_gb:.1f}GB available"
    except Exception as e:
        return f"error: {str(e)}"


def count_files(path: Path) -> int:
    """Count files in directory"""
    try:
        if not path.exists():
            return 0
        return len([f for f in path.rglob("*") if f.is_file()])
    except Exception:
        return 0