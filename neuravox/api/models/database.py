"""SQLAlchemy database models for Neuravox API"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Text, Integer, BigInteger, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from neuravox.db.database import Base


def generate_uuid() -> str:
    """Generate UUID string"""
    return str(uuid4())


class Job(Base):
    """Job tracking table"""
    __tablename__ = "jobs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    job_type: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    config_override: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    result_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    job_files: Mapped[list["JobFile"]] = relationship("JobFile", back_populates="job", cascade="all, delete-orphan")


class File(Base):
    """File metadata table"""
    __tablename__ = "files"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Relationships
    job_files: Mapped[list["JobFile"]] = relationship("JobFile", back_populates="file", cascade="all, delete-orphan")


class JobFile(Base):
    """Job-File relationship table"""
    __tablename__ = "job_files"
    
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("files.id", ondelete="CASCADE"), primary_key=True)
    file_role: Mapped[str] = mapped_column(String(20), nullable=False, primary_key=True)
    
    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="job_files")
    file: Mapped["File"] = relationship("File", back_populates="job_files")


class ApiKey(Base):
    """API key authentication table"""
    __tablename__ = "api_keys"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=60)