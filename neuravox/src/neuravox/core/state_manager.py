"""
SQLite-based state management for pipeline processing
"""
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from contextlib import contextmanager

class StateManager:
    """SQLite-based state management"""
    
    def __init__(self, workspace_path: Path):
        self.db_path = workspace_path / '.pipeline_state.db'
        self.workspace_path = workspace_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    file_id TEXT PRIMARY KEY,
                    original_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS processing_stages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT REFERENCES files(file_id),
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    metadata TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT REFERENCES files(file_id),
                    chunk_index INTEGER,
                    audio_path TEXT,
                    transcript_path TEXT,
                    start_time REAL,
                    end_time REAL,
                    transcribed BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Create indices for better performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_files_status ON files(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_stages_file_id ON processing_stages(file_id)')
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper cleanup"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def start_processing(self, file_id: str, original_path: str):
        """Mark file as started processing"""
        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO files (file_id, original_path, status, updated_at)
                VALUES (?, ?, 'processing', datetime('now'))
            ''', (file_id, original_path))
            
            conn.execute('''
                INSERT INTO processing_stages (file_id, stage, status, started_at)
                VALUES (?, 'processing', 'started', datetime('now'))
            ''', (file_id,))
    
    def update_stage(self, file_id: str, stage: str, metadata: Optional[Dict] = None):
        """Update processing stage"""
        with self._get_connection() as conn:
            # Complete previous stage
            conn.execute('''
                UPDATE processing_stages 
                SET status = 'completed', completed_at = datetime('now')
                WHERE file_id = ? AND status = 'started'
            ''', (file_id,))
            
            # Start new stage
            metadata_json = json.dumps(metadata) if metadata else None
            conn.execute('''
                INSERT INTO processing_stages (file_id, stage, status, started_at, metadata)
                VALUES (?, ?, 'started', datetime('now'), ?)
            ''', (file_id, stage, metadata_json))
            
            # Update file status
            conn.execute('''
                UPDATE files SET status = ?, updated_at = datetime('now')
                WHERE file_id = ?
            ''', (stage, file_id))
    
    def complete_processing(self, file_id: str):
        """Mark file as completed"""
        with self._get_connection() as conn:
            conn.execute('''
                UPDATE processing_stages 
                SET status = 'completed', completed_at = datetime('now')
                WHERE file_id = ? AND status = 'started'
            ''', (file_id,))
            
            conn.execute('''
                UPDATE files SET status = 'completed', updated_at = datetime('now')
                WHERE file_id = ?
            ''', (file_id,))
    
    def mark_failed(self, file_id: str, error_message: str):
        """Mark file as failed"""
        with self._get_connection() as conn:
            conn.execute('''
                UPDATE processing_stages 
                SET status = 'failed', completed_at = datetime('now'), error_message = ?
                WHERE file_id = ? AND status = 'started'
            ''', (error_message, file_id))
            
            conn.execute('''
                UPDATE files SET status = 'failed', updated_at = datetime('now')
                WHERE file_id = ?
            ''', (file_id,))
    
    def get_file_status(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a file"""
        with self._get_connection() as conn:
            row = conn.execute('''
                SELECT * FROM files WHERE file_id = ?
            ''', (file_id,)).fetchone()
            
            if row:
                return dict(row)
            return None
    
    def get_failed_files(self) -> List[Dict[str, Any]]:
        """Get list of failed files with details"""
        with self._get_connection() as conn:
            rows = conn.execute('''
                SELECT f.file_id, f.original_path, f.created_at, ps.error_message
                FROM files f
                LEFT JOIN processing_stages ps ON f.file_id = ps.file_id
                WHERE f.status = 'failed' AND ps.status = 'failed'
                ORDER BY f.created_at DESC
            ''').fetchall()
            
            return [dict(row) for row in rows]
    
    def get_processing_history(self, file_id: str) -> List[Dict[str, Any]]:
        """Get processing history for a file"""
        with self._get_connection() as conn:
            rows = conn.execute('''
                SELECT stage, status, started_at, completed_at, error_message, metadata
                FROM processing_stages
                WHERE file_id = ?
                ORDER BY started_at
            ''', (file_id,)).fetchall()
            
            history = []
            for row in rows:
                item = dict(row)
                if item['metadata']:
                    item['metadata'] = json.loads(item['metadata'])
                history.append(item)
            
            return history
    
    def get_pipeline_summary(self) -> Dict[str, Any]:
        """Get overall pipeline summary"""
        with self._get_connection() as conn:
            # Count files by status
            status_counts = {}
            rows = conn.execute('''
                SELECT status, COUNT(*) as count
                FROM files
                GROUP BY status
            ''').fetchall()
            
            for row in rows:
                status_counts[row['status']] = row['count']
            
            # Get recent activity
            recent_files = conn.execute('''
                SELECT file_id, original_path, status, created_at, updated_at
                FROM files
                ORDER BY updated_at DESC
                LIMIT 10
            ''').fetchall()
            
            return {
                'status_counts': status_counts,
                'total_files': sum(status_counts.values()),
                'recent_activity': [dict(row) for row in recent_files]
            }
    
    def cleanup_old_records(self, days: int = 30):
        """Clean up old records"""
        with self._get_connection() as conn:
            conn.execute('''
                DELETE FROM files
                WHERE updated_at < datetime('now', '-{} days')
                AND status IN ('completed', 'failed')
            '''.format(days))
            
            # Clean up orphaned stage records
            conn.execute('''
                DELETE FROM processing_stages
                WHERE file_id NOT IN (SELECT file_id FROM files)
            ''')
            
            # Clean up orphaned chunk records
            conn.execute('''
                DELETE FROM chunks
                WHERE file_id NOT IN (SELECT file_id FROM files)
            ''')