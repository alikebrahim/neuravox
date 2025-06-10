"""File upload, download, and management endpoints"""

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from neuravox.db.database import get_db_session
from neuravox.shared.config import UnifiedConfig
from neuravox.api.services.file_service import FileService
from neuravox.api.models.responses import FileMetadataResponse, UploadResponse
from neuravox.api.utils.exceptions import NotFoundError, ValidationError
from neuravox.api.middleware.auth import get_current_user_id


router = APIRouter()


def get_file_service() -> FileService:
    """Dependency for file service"""
    config = UnifiedConfig()
    return FileService(config)


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    user_id: Optional[str] = Depends(get_current_user_id),
    file_service: FileService = Depends(get_file_service),
    db: AsyncSession = Depends(get_db_session)
):
    """Upload an audio file"""
    
    try:
        db_file = await file_service.upload_file(file, user_id, db)
        
        return UploadResponse(
            id=db_file.id,
            filename=db_file.filename,
            size=db_file.file_size,
            message="File uploaded successfully"
        )
    
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/files", response_model=List[FileMetadataResponse])
async def list_files(
    limit: int = 50,
    offset: int = 0,
    user_id: Optional[str] = Depends(get_current_user_id),
    file_service: FileService = Depends(get_file_service),
    db: AsyncSession = Depends(get_db_session)
):
    """List uploaded files"""
    
    files = await file_service.list_files(db, user_id, limit, offset)
    
    response_files = []
    for f in files:
        # Get audio metadata if available
        audio_metadata = None
        if f.file_path:
            file_path = Path(f.file_path)
            if file_path.exists():
                audio_metadata = file_service.get_audio_metadata(file_path)
        
        response_files.append(
            FileMetadataResponse(
                id=f.id,
                filename=f.filename,
                original_filename=f.original_filename,
                size=f.file_size,
                mime_type=f.mime_type,
                uploaded_at=f.uploaded_at,
                download_url=f"/api/v1/files/{f.id}/download",
                audio=audio_metadata
            )
        )
    
    return response_files


@router.get("/files/{file_id}", response_model=FileMetadataResponse)
async def get_file_metadata(
    file_id: str,
    file_service: FileService = Depends(get_file_service),
    db: AsyncSession = Depends(get_db_session)
):
    """Get file metadata by ID"""
    
    try:
        file = await file_service.get_file(file_id, db)
        
        # Get audio metadata if available
        audio_metadata = None
        if file.file_path:
            file_path = Path(file.file_path)
            if file_path.exists():
                audio_metadata = file_service.get_audio_metadata(file_path)
        
        return FileMetadataResponse(
            id=file.id,
            filename=file.filename,
            original_filename=file.original_filename,
            size=file.file_size,
            mime_type=file.mime_type,
            uploaded_at=file.uploaded_at,
            download_url=f"/api/v1/files/{file.id}/download",
            audio=audio_metadata
        )
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file: {str(e)}")


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: str,
    file_service: FileService = Depends(get_file_service),
    db: AsyncSession = Depends(get_db_session)
):
    """Download a file"""
    
    try:
        file = await file_service.get_file(file_id, db)
        file_path = file_service.get_download_path(file)
        
        return FileResponse(
            path=str(file_path),
            filename=file.original_filename,
            media_type=file.mime_type or 'application/octet-stream'
        )
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.delete("/files/{file_id}", status_code=204)
async def delete_file(
    file_id: str,
    file_service: FileService = Depends(get_file_service),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a file"""
    
    try:
        await file_service.delete_file(file_id, db)
        return
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@router.get("/workspace/files")
async def list_workspace_files(
    file_service: FileService = Depends(get_file_service)
):
    """List all files in workspace directories"""
    
    try:
        files = await file_service.list_workspace_files()
        return {
            "files": files,
            "total": len(files),
            "message": "Workspace files listed successfully"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list workspace files: {str(e)}")