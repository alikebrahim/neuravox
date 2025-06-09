"""
Common file handling utilities
"""
from pathlib import Path
from typing import List, Optional, Tuple
import shutil
import hashlib
import json

def ensure_directory(path: Path) -> Path:
    """Ensure directory exists, create if not"""
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_audio_files(directory: Path, extensions: Optional[List[str]] = None) -> List[Path]:
    """Get all audio files in directory"""
    if extensions is None:
        extensions = ['.mp3', '.wav', '.flac', '.m4a', '.ogg', '.opus', '.wma', '.aac']
    
    audio_files = []
    for ext in extensions:
        audio_files.extend(directory.glob(f'*{ext}'))
        audio_files.extend(directory.glob(f'*{ext.upper()}'))
    
    return sorted(set(audio_files))

def move_file_safely(src: Path, dst: Path) -> Path:
    """Move file safely, handling existing files"""
    if dst.exists():
        # Add number suffix to avoid overwriting
        base = dst.stem
        ext = dst.suffix
        counter = 1
        while dst.exists():
            dst = dst.parent / f"{base}_{counter}{ext}"
            counter += 1
    
    shutil.move(str(src), str(dst))
    return dst

def calculate_file_hash(file_path: Path, chunk_size: int = 8192) -> str:
    """Calculate SHA256 hash of file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def create_file_id(file_path: Path) -> str:
    """Create unique file ID from path"""
    # Use first 8 chars of hash + filename stem
    file_hash = calculate_file_hash(file_path)[:8]
    return f"{file_path.stem}_{file_hash}"

def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable string"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def format_file_size(size_bytes: int) -> str:
    """Format file size to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def load_json_file(path: Path) -> dict:
    """Load JSON file with error handling"""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        raise ValueError(f"Error loading JSON from {path}: {e}")

def save_json_file(data: dict, path: Path, indent: int = 2):
    """Save data to JSON file"""
    ensure_directory(path.parent)
    with open(path, 'w') as f:
        json.dump(data, f, indent=indent, default=str)

def get_relative_path(path: Path, base: Path) -> Path:
    """Get relative path from base, handling when path is not relative to base"""
    try:
        return path.relative_to(base)
    except ValueError:
        return path

def cleanup_empty_directories(base_path: Path):
    """Remove empty directories recursively"""
    for dirpath in sorted(base_path.rglob('*'), reverse=True):
        if dirpath.is_dir() and not any(dirpath.iterdir()):
            dirpath.rmdir()