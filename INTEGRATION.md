# INTEGRATION.md - Monorepo Audio Processing & Transcription Platform

## Project Overview

This document outlines the plan for merging audio_processor and ai_transcriber into a cohesive monorepo platform with unified interface, shared dependencies, and seamless workflow integration.

## Architecture Design

### Core Principles
1. **Monorepo Structure**: Single cohesive project with modular components
2. **Unified Dependencies**: One set of dependencies managed by uv
3. **Seamless Integration**: Direct module communication without adapters
4. **API-First Design**: REST endpoints for future mobile/web clients
5. **Progressive Enhancement**: Modules work standalone or in pipeline mode

### Directory Structure
```
audio_workflow_platform/
├── modules/
│   ├── audio_processor/    # Refactored from original
│   │   ├── __init__.py
│   │   ├── splitter.py
│   │   ├── optimizer.py
│   │   └── metadata.py
│   ├── transcriber/        # Refactored from ai_transcriber
│   │   ├── __init__.py
│   │   ├── models/
│   │   ├── batch_processor.py
│   │   └── chunk_merger.py
│   └── shared/             # Shared utilities
│       ├── __init__.py
│       ├── config.py
│       ├── metadata.py
│       └── file_utils.py
├── api/                    # REST API for mobile/web
│   ├── __init__.py
│   ├── app.py             # FastAPI application
│   ├── routers/
│   │   ├── audio.py
│   │   └── transcription.py
│   └── models.py
├── cli/                    # Unified CLI
│   ├── __init__.py
│   └── main.py
├── core/                   # Core business logic
│   ├── __init__.py
│   ├── pipeline.py        # Main workflow orchestration
│   ├── state_manager.py   # SQLite state tracking
│   ├── file_watcher.py    # File monitoring service
│   └── batch_manager.py   # Dynamic batching logic
├── config/
│   ├── default.yaml       # Default configuration
│   └── prompts.toml       # Transcription prompts
├── pyproject.toml         # Unified dependencies
└── INTEGRATION.md         # This file

# Installation location
~/.local/bin/unified-audio   # Executable entry point
~/.local/share/unified-audio/ # Application data
~/.config/unified-audio/     # User configuration

# User workspace (configurable)
~/audio_notes/              # Default workspace
├── input/                  # Raw audio files
├── processed/              # Audio processor output
│   └── chunks/            # Chunked audio files
└── transcribed/           # Final transcriptions
```

## Unified Dependencies

### Resolved Dependencies (pyproject.toml)
```toml
[project]
name = "audio-workflow-platform"
version = "1.0.0"
requires-python = ">=3.12"

[project.dependencies]
# Audio processing
librosa = ">=0.11.0"
soundfile = ">=0.13.0"
scipy = ">=1.6.0"
numpy = ">=1.24.0"

# AI/Transcription
google-genai = ">=0.8.0"
openai = ">=1.0.0"

# CLI and UI
typer = {extras = ["all"], version = ">=0.12.0"}
rich = ">=13.0.0"
tqdm = ">=4.66.0"

# API
fastapi = ">=0.110.0"
uvicorn = {extras = ["standard"], version = ">=0.27.0"}

# Configuration
pydantic = ">=2.0.0"
pyyaml = ">=6.0"
toml = ">=0.10.2"

# Utilities
requests = ">=2.31.0"
psutil = ">=5.9.0"
watchdog = ">=4.0.0"  # For file monitoring
sqlalchemy = ">=2.0.0"  # For state management

[project.scripts]
audio-workflow = "cli.main:app"
audio-api = "api.app:run_server"
```

## Module Improvements Required

### 1. Audio Processor Enhancements
- **Add Pipeline Mode**: Return structured data instead of just files
- **Chunk Metadata Enhancement**: Add sequence numbers and parent references
- **Callback System**: Emit events when chunks are ready
- **API Integration**: Direct memory processing without file I/O

### 2. Transcriber Enhancements  
- **Chunk-Aware Processing**: Accept pre-split chunks with metadata
- **Transcript Merging**: Combine chunk transcripts with timestamps
- **Pipeline Integration**: Skip full file processing when chunks exist
- **Progress Callbacks**: Real-time updates for API/GUI

### 3. New Shared Components
- **Unified Metadata Schema**: Consistent format across modules
- **Event System**: For inter-module communication
- **Configuration Manager**: Single source of truth
- **File Manager**: Handle workspace organization

## File Watching Mechanisms - Decision Framework

### Option 1: Local File System Monitoring (watchdog)
**Pros:**
- Real-time detection of new files
- Low resource usage (inotify on Linux)
- Can detect file modifications/deletions
- Works offline
- No polling overhead

**Cons:**
- Limited to local file system
- Platform-specific behaviors
- Can miss events if service stops
- Requires daemon process

**Features:**
- Event types: created, modified, deleted, moved
- Can watch multiple directories
- Configurable event filters

**Best for:** Desktop applications, local workflows

### Option 2: Polling-Based Detection
**Pros:**
- Simple and reliable
- Works across all platforms
- Can handle network drives
- Easy to implement retry logic
- Controllable resource usage

**Cons:**
- Delay based on polling interval
- Higher resource usage for large directories
- May miss rapid changes

**Features:**
- Configurable intervals (e.g., 5-60 seconds)
- Can include file stability checks
- Works with remote filesystems

**Best for:** Network drives, cross-platform needs

### Option 3: Event-Driven API Uploads
**Pros:**
- Perfect for mobile/web clients
- Immediate processing trigger
- No background monitoring needed
- Scales with demand
- Direct progress feedback

**Cons:**
- Requires active upload
- No automatic local folder sync
- Needs API infrastructure

**Features:**
- REST endpoint triggers processing
- WebSocket for progress updates
- Direct client feedback

**Best for:** Mobile apps, web interfaces

### Recommended Hybrid Approach
```python
file_monitoring:
  strategies:
    - local_watch:     # For desktop users
        enabled: true
        method: "watchdog"
        paths: ["~/audio_notes/input"]
    - api_upload:      # For mobile/web
        enabled: true
        endpoint: "/api/upload"
    - polling:         # Fallback/network drives
        enabled: false
        interval: 30
```

## REST API Design for Mobile/Web Clients

### Authentication (Minimal)
```python
# Simple token-based auth for private use
auth:
  enabled: true
  type: "bearer_token"
  tokens:
    - "your-secret-token-here"  # Environment variable in production
```

### Core Endpoints
```python
# File Upload & Processing
POST   /api/upload              # Upload audio file
POST   /api/process/{file_id}   # Start processing
GET    /api/status/{file_id}    # Check processing status

# Batch Operations  
POST   /api/batch/upload        # Upload multiple files
GET    /api/batch/{batch_id}    # Batch status

# Results
GET    /api/transcript/{file_id}  # Get transcription
GET    /api/metadata/{file_id}    # Get processing metadata
GET    /api/files                 # List all files

# Configuration
GET    /api/models               # Available transcription models
PUT    /api/config               # Update configuration

# WebSocket
WS     /api/ws/{file_id}        # Real-time progress updates
```

### API Response Models
```python
class ProcessingStatus(BaseModel):
    file_id: str
    status: Literal["queued", "processing", "transcribing", "completed", "failed"]
    progress: float  # 0.0 to 1.0
    current_step: str
    chunks_processed: int
    total_chunks: int
    error: Optional[str]

class TranscriptionResult(BaseModel):
    file_id: str
    original_filename: str
    transcript: str
    chunks: List[ChunkInfo]
    metadata: ProcessingMetadata
    created_at: datetime
```

### 4. File Flow Management

```
workspace/
├── input/
│   ├── episode1.mp3         # Original files
│   └── episode2.wav
├── processed/
│   ├── episode1/
│   │   ├── episode1_full.flac
│   │   ├── episode1_chunk_001.flac
│   │   ├── episode1_chunk_002.flac
│   │   └── metadata.json
│   └── episode2/
│       ├── episode2_full.flac
│       └── metadata.json
└── transcribed/
    ├── episode1/
    │   ├── episode1_full_transcript.md
    │   ├── episode1_chunk_001_transcript.md
    │   ├── episode1_chunk_002_transcript.md
    │   └── episode1_summary.json
    └── episode2/
        ├── episode2_full_transcript.md
        └── episode2_summary.json
```

## Additional Decisions Required

### 1. API Key Management
**Options:**
- A) Store in unified config file with encryption
- B) Environment variables only
- C) Secure key vault integration (e.g., system keyring)

**Considerations:** Security vs convenience for private use

### 2. Chunk Boundary Handling
**Options:**
- A) Simple concatenation (may split sentences)
- B) Smart merging with overlap detection
- C) Re-transcribe boundary regions with context

**Considerations:** Accuracy vs processing time

### 3. File Storage for API
**Options:**
- A) Local filesystem with UUID paths
- B) S3-compatible object storage
- C) Hybrid (local processing, cloud archive)

**Considerations:** Scalability vs complexity

### 4. Processing Priority/Queue
**Options:**
- A) FIFO queue
- B) Priority based on file size
- C) User-defined priorities

**Considerations:** Fairness vs optimization

### 5. Transcription Caching
**Options:**
- A) Cache all transcriptions indefinitely
- B) Time-based expiration
- C) LRU cache with size limits

**Considerations:** Storage vs re-processing costs

## Monorepo Migration Strategy

### Phase 1: Repository Structure
```bash
# Create new monorepo structure
audio-workflow-platform/
├── modules/
│   ├── processor/     # Migrate from audio_processor
│   ├── transcriber/   # Migrate from ai_transcriber  
│   └── shared/        # Extract common code
├── api/               # New REST API
├── cli/               # Unified CLI
├── core/              # Business logic
└── tests/             # Unified test suite
```

### Phase 2: Code Refactoring

#### Shared Components to Extract
1. **File handling** (both modules have similar patterns)
2. **Metadata structures** (unify JSON schemas)
3. **Configuration loading** (merge YAML/TOML/JSON)
4. **Progress tracking** (standardize callbacks)

#### Module-Specific Refactoring

**Audio Processor:**
```python
# Before: Standalone script
def process_audio_file(input_path, output_dir):
    # Process and save files
    
# After: Pipeline-aware module  
class AudioProcessor:
    def process(self, input_path, config):
        # Return structured result
        return ProcessingResult(
            chunks=[...],
            metadata={...},
            file_paths=[...]
        )
```

**Transcriber:**
```python
# Before: Single file transcription
def transcribe_file(audio_path, model):
    # Transcribe one file
    
# After: Chunk-aware transcription
class Transcriber:
    def transcribe_chunks(self, chunk_data, model):
        # Process chunks with metadata
        # Return combined transcript
```

### Phase 3: Database Schema
```sql
-- Unified state tracking
CREATE TABLE files (
    id TEXT PRIMARY KEY,
    original_name TEXT NOT NULL,
    upload_source TEXT, -- 'local', 'api', 'watch'
    status TEXT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE processing_stages (
    id INTEGER PRIMARY KEY,
    file_id TEXT REFERENCES files(id),
    stage TEXT NOT NULL, -- 'upload', 'process', 'transcribe'
    status TEXT NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    metadata JSON
);

CREATE TABLE chunks (
    id INTEGER PRIMARY KEY,
    file_id TEXT REFERENCES files(id),
    chunk_index INTEGER,
    audio_path TEXT,
    transcript_path TEXT,
    start_time REAL,
    end_time REAL,
    transcribed BOOLEAN DEFAULT FALSE
);
```

## Technical Implementation Details

### Core Components

#### 1. Orchestrator Class
```python
class AudioPipelineOrchestrator:
    def __init__(self, config_path):
        self.config = load_config(config_path)
        self.audio_processor = AudioProcessorWrapper(config)
        self.transcriber = TranscriberWrapper(config)
        
    def run_pipeline(self, files, interactive=True):
        # Orchestrate the full pipeline
        pass
        
    def get_pipeline_status(self):
        # Return current state of all files
        pass
```

#### 2. CLI Wrapper Classes
```python
class AudioProcessorWrapper:
    def process_files(self, input_files, options):
        # Build and execute audio_processor CLI command
        # Parse output and return results
        pass

class TranscriberWrapper:
    def transcribe_files(self, input_files, model, project):
        # Build and execute ai_transcriber CLI command
        # Parse output and return results
        pass
```

#### 3. State Management
```python
class PipelineState:
    def __init__(self, workspace_path):
        self.workspace = workspace_path
        self.state_file = workspace_path / ".pipeline_state.json"
        
    def mark_processed(self, file_path):
        # Track processing status
        pass
        
    def get_pending_transcriptions(self):
        # Return files ready for transcription
        pass
```

## Next Steps

1. **Create new monorepo** with unified structure
2. **Migrate and refactor** existing modules
3. **Implement shared components** (config, metadata, file handling)
4. **Build pipeline orchestrator** with SQLite state management
5. **Create unified CLI** with rich interface
6. **Implement REST API** with FastAPI
7. **Add file monitoring** service (hybrid approach)
8. **Create chunk merger** for seamless transcriptions
9. **Write comprehensive tests** for all components
10. **Document deployment** and configuration

## Final Design Decisions

### Architecture
- **Monorepo approach** with unified dependencies managed by uv
- **Direct code integration** for optimal performance
- **Python 3.12+** as the minimum version
- **REST API** to be developed in later phase

### Configuration Management
- **API Keys**: Support both environment variables and config file
- **Unified config system** with hierarchy: env vars > config file > defaults

### Processing Decisions
- **Chunk Boundary**: Start with simple concatenation (can enhance later)
- **File Storage**: Local filesystem only
- **Processing Priority**: FIFO queue
- **Transcription Caching**: Not needed for current use case

### File Monitoring Strategy
**Phase 1 (Current)**: 
- CLI interactive mode with manual file selection
- Scan input directory on demand

**Phase 2 (Future with mobile app)**:
- Background service with watchdog
- File stability detection (wait for upload completion)
- Automatic processing trigger
- Notification system for completion

### Development Priorities
1. **Focus on core workflow** (processor → transcriber)
2. **Build as future server** for mobile app
3. **REST API development** deferred to later phase

## Implementation Roadmap

### Phase 1: Core Platform Development
1. **Create monorepo structure** with unified dependencies
2. **Migrate modules** with minimal refactoring:
   - Extract shared components
   - Add pipeline mode to audio_processor
   - Add chunk-aware processing to transcriber
3. **Implement unified configuration**:
   - Config file + env var support
   - API key management system
4. **Build workflow orchestrator**:
   - SQLite state management
   - FIFO processing queue
   - Resume capability
5. **Create unified CLI**:
   - Interactive file selection
   - Rich progress display
   - Status and resume commands

### Phase 2: Service Preparation (Future)
1. **Add file monitoring service** (disabled by default)
2. **Create REST API structure** (skeleton only)
3. **Implement notification system** hooks
4. **Add file stability detection** for uploads
5. **Document API design** for mobile app

### Configuration Example
```yaml
# config/default.yaml
workspace:
  base_path: "~/audio_notes"
  
api_keys:
  # Can be overridden by env vars
  google_gemini: ${GOOGLE_API_KEY}
  openai: ${OPENAI_API_KEY}
  
processing:
  chunk_boundary: "simple"  # or "smart" in future
  
service:
  mode: "cli"  # or "service" when ready
  file_watch:
    enabled: false
    stability_check: true
    stability_timeout: 5
```

## Architecture Decision: Import vs CLI

### Why Import Over CLI Orchestration
Given the future GUI/mobile app requirements, importing code provides:
1. **Real-time progress callbacks** for responsive UI
2. **Rich error information** with stack traces
3. **Direct memory access** for large file handling
4. **Cancellation support** for long operations
5. **Shared state** without serialization overhead
6. **Native Python debugging** capabilities

### Maintaining Module Independence
Despite importing, we preserve independence through:
1. **Adapter pattern** isolating module interfaces
2. **Git submodules** for separate version control
3. **No direct modifications** to original modules
4. **Clear API boundaries** in adapters
5. **Fallback to CLI** if imports fail

## Benefits of This Approach

1. **Future-ready**: Direct path to GUI/mobile apps
2. **High performance**: No process spawning overhead
3. **Resumable**: SQLite-based state management
4. **Flexible**: Configurable workspace locations
5. **Maintainable**: Clear separation through adapters
6. **User-friendly**: Modern CLI with progress tracking

## Potential Future Enhancements

1. **Web UI**: Add Flask/FastAPI web interface
2. **Parallel Processing**: Process multiple files simultaneously
3. **Cloud Integration**: Support cloud storage for input/output
4. **Webhook Notifications**: Notify when processing completes
5. **Plugin System**: Allow custom processing steps
6. **Analytics**: Track processing times and success rates