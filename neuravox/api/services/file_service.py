"""File management service for API"""

import hashlib
import mimetypes
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from neuravox.api.models.database import File
from neuravox.api.utils.exceptions import NotFoundError, ValidationError
from neuravox.shared.config import UnifiedConfig
from neuravox.shared.file_utils import get_audio_files


class FileService:
    """Service for managing file operations"""
    
    def __init__(self, config: UnifiedConfig):
        self.config = config
    
    async def upload_file(
        self, 
        upload_file: UploadFile, 
        user_id: Optional[str],
        db: AsyncSession
    ) -> File:
        """Upload and store a file"""
        
        # Validate file
        if not upload_file.filename:
            raise ValidationError("Filename is required")
        
        # Check file size (1GB limit)
        max_size = 1024 * 1024 * 1024  # 1GB
        content = await upload_file.read()
        if len(content) > max_size:
            raise ValidationError(f"File too large. Maximum size is {max_size} bytes")
        
        # Validate audio file
        if not self._is_audio_file(upload_file.filename):
            raise ValidationError("Only audio files are supported")
        
        # Generate unique file ID and paths
        file_id = str(uuid4())
        file_extension = Path(upload_file.filename).suffix
        stored_filename = f"{file_id}{file_extension}"
        file_path = self.config.input_path / stored_filename
        
        # Ensure input directory exists
        self.config.input_path.mkdir(parents=True, exist_ok=True)
        
        # Calculate checksum
        checksum = hashlib.sha256(content).hexdigest()
        
        # Save file to disk
        try:
            with open(file_path, "wb") as f:
                f.write(content)
        except Exception as e:
            raise ValidationError(f"Failed to save file: {str(e)}")
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(upload_file.filename)
        
        # Extract audio metadata
        audio_metadata = self.get_audio_metadata(file_path)
        
        # Create database record
        db_file = File(
            id=file_id,
            filename=stored_filename,
            original_filename=upload_file.filename,
            file_path=str(file_path),
            file_size=len(content),
            mime_type=mime_type,
            checksum=checksum,
            user_id=user_id
        )
        
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)
        
        return db_file
    
    async def get_file(self, file_id: str, db: AsyncSession) -> File:
        """Get file by ID"""
        result = await db.execute(select(File).where(File.id == file_id))
        file = result.scalar_one_or_none()
        
        if not file:
            raise NotFoundError("File", file_id)
        
        return file
    
    async def list_files(
        self, 
        db: AsyncSession,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[File]:
        """List files with pagination"""
        query = select(File)
        
        if user_id:
            query = query.where(File.user_id == user_id)
        
        query = query.limit(limit).offset(offset).order_by(File.uploaded_at.desc())
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def delete_file(self, file_id: str, db: AsyncSession) -> bool:
        """Delete a file"""
        file = await self.get_file(file_id, db)
        
        # Delete from filesystem
        file_path = Path(file.file_path)
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass  # Continue with database deletion even if file removal fails
        
        # Delete from database
        await db.delete(file)
        await db.commit()
        
        return True
    
    def get_download_path(self, file: File) -> Path:
        """Get the file path for download"""
        file_path = Path(file.file_path)
        
        if not file_path.exists():
            raise NotFoundError("File on disk", file.filename)
        
        return file_path
    
    def _is_audio_file(self, filename: str) -> bool:
        """Check if file is an audio file"""
        audio_extensions = {
            '.mp3', '.wav', '.flac', '.m4a', '.ogg', 
            '.opus', '.wma', '.aac', '.mp4'
        }
        
        return Path(filename).suffix.lower() in audio_extensions
    
    async def list_workspace_files(self) -> List[dict]:
        """List files in workspace directories"""
        files = []
        
        # Input files
        if self.config.input_path.exists():
            for file_path in get_audio_files(self.config.input_path):
                files.append({
                    "path": str(file_path),
                    "name": file_path.name,
                    "size": file_path.stat().st_size,
                    "location": "input",
                    "type": "audio"
                })
        
        # Processed files
        if self.config.processed_path.exists():
            for file_path in self.config.processed_path.rglob("*"):
                if file_path.is_file():
                    files.append({
                        "path": str(file_path),
                        "name": file_path.name,
                        "size": file_path.stat().st_size,
                        "location": "processed",
                        "type": "processed"
                    })
        
        # Transcribed files
        if self.config.transcribed_path.exists():
            for file_path in self.config.transcribed_path.rglob("*"):
                if file_path.is_file():
                    files.append({
                        "path": str(file_path),
                        "name": file_path.name,
                        "size": file_path.stat().st_size,
                        "location": "transcribed",
                        "type": "transcribed"
                    })
        
        return files
    
    def get_audio_metadata(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Extract audio metadata from file"""
        try:
            from pydub import AudioSegment
            from pydub.utils import mediainfo
            
            # Get basic info using pydub
            info = mediainfo(str(file_path))
            
            if not info:
                return None
            
            # Extract relevant metadata
            metadata = {
                "duration": float(info.get("duration", 0)),
                "sample_rate": int(info.get("sample_rate", 0)),
                "channels": int(info.get("channels", 0)),
                "bit_rate": int(info.get("bit_rate", 0)) if info.get("bit_rate") else None,
                "codec": info.get("codec_name"),
                "format": info.get("format_name")
            }
            
            # Try to get bit depth if available
            if "bits_per_raw_sample" in info:
                metadata["bit_depth"] = int(info["bits_per_raw_sample"])
            elif "bits_per_sample" in info:
                metadata["bit_depth"] = int(info["bits_per_sample"])
            
            return metadata
            
        except Exception:
            # If we can't extract metadata, return None
            return None