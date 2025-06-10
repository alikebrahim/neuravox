"""Workspace management endpoints"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from neuravox.shared.config import UnifiedConfig
from neuravox.api.middleware.auth import require_api_key


router = APIRouter()


class WorkspaceInitRequest(BaseModel):
    """Request for workspace initialization"""
    workspace_path: Optional[str] = None


class WorkspaceInitResponse(BaseModel):
    """Response for workspace initialization"""
    workspace: str
    input_path: str
    processed_path: str
    transcribed_path: str
    message: str


class WorkspaceStatusResponse(BaseModel):
    """Response for workspace status"""
    workspace: str
    input_path: str
    processed_path: str
    transcribed_path: str
    input_files_count: int
    processed_files_count: int
    transcribed_files_count: int
    exists: bool


@router.post("/workspace/init", response_model=WorkspaceInitResponse)
async def initialize_workspace(
    request: WorkspaceInitRequest = WorkspaceInitRequest(),
    _api_key = Depends(require_api_key)
):
    """Initialize workspace directories (mirrors CLI 'init' command)"""
    
    try:
        config = UnifiedConfig()
        
        # Override workspace path if provided
        if request.workspace_path:
            config.workspace = Path(request.workspace_path).expanduser()
        
        # Create workspace directories
        config.ensure_workspace_dirs()
        
        return WorkspaceInitResponse(
            workspace=str(config.workspace),
            input_path=str(config.input_path),
            processed_path=str(config.processed_path),
            transcribed_path=str(config.transcribed_path),
            message="Workspace initialized successfully"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize workspace: {str(e)}")


@router.get("/workspace/status", response_model=WorkspaceStatusResponse)
async def get_workspace_status(
    workspace_path: Optional[str] = None,
    _api_key = Depends(require_api_key)
):
    """Get workspace status and file counts"""
    
    try:
        config = UnifiedConfig()
        
        # Override workspace path if provided
        if workspace_path:
            config.workspace = Path(workspace_path).expanduser()
        
        # Check if workspace exists
        exists = config.workspace.exists()
        
        # Count files in each directory
        input_count = 0
        processed_count = 0
        transcribed_count = 0
        
        if exists:
            from neuravox.shared.file_utils import get_audio_files
            
            if config.input_path.exists():
                input_count = len(list(get_audio_files(config.input_path)))
            
            if config.processed_path.exists():
                processed_count = len(list(config.processed_path.rglob("*.flac")))
            
            if config.transcribed_path.exists():
                transcribed_count = len(list(config.transcribed_path.rglob("*.md")))
        
        return WorkspaceStatusResponse(
            workspace=str(config.workspace),
            input_path=str(config.input_path),
            processed_path=str(config.processed_path),
            transcribed_path=str(config.transcribed_path),
            input_files_count=input_count,
            processed_files_count=processed_count,
            transcribed_files_count=transcribed_count,
            exists=exists
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workspace status: {str(e)}")