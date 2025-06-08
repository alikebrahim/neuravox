# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Neuravox is a neural audio processing platform that provides:
1. **Audio Processing**: Sophisticated silence-based audio splitting and optimization
2. **AI Transcription**: Multi-model transcription with chunk support

The platform provides a seamless pipeline for processing audio files through both stages.

## Common Development Commands

### Setup and Installation
```bash
# Create virtual environment and install
uv venv
source .venv/bin/activate
uv pip install -e .

# Initialize workspace
neuravox init
```

### Running the Platform
```bash
# Interactive processing (recommended)
neuravox process --interactive

# Process specific files
neuravox process file1.mp3 file2.wav

# Check status
neuravox status

# Resume failed jobs
neuravox resume
```

### Development Commands
```bash
# Run tests
pytest

# Run specific test module
pytest tests/unit/test_pipeline.py

# Lint code
ruff check .

# Format code
ruff format .
```

## Architecture & Key Components

### Module Structure
- **modules/processor**: Audio processing logic
  - `audio_splitter.py`: Core silence detection and splitting (25-second threshold)
  - `metadata_output.py`: Metadata generation and export
  - `cli.py`: Processor CLI interface

- **modules/transcriber**: Transcription logic  
  - `engine.py`: Core transcription engine with model support
  - `models/`: Provider implementations (Google, OpenAI, Ollama)
  - `config.py`: Configuration management

- **modules/shared**: Common components
  - `config.py`: Unified configuration with env var support
  - `metadata.py`: Shared metadata structures
  - `progress.py`: Unified progress tracking
  - `file_utils.py`: Common file operations

- **core**: Pipeline orchestration
  - `pipeline.py`: Main workflow orchestrator
  - `state_manager.py`: SQLite-based state tracking
  - `exceptions.py`: Custom exception hierarchy

- **cli**: Unified command-line interface
  - `main.py`: Typer-based CLI with rich formatting

### Key Design Decisions

1. **Unified Architecture**: Single project with integrated dependencies
2. **Pipeline Processing**: Modules work together in a seamless pipeline
3. **State Management**: SQLite for resume capability and progress tracking
4. **Configuration Hierarchy**: env vars > config file > defaults
5. **Chunk Processing**: Always process chunks only, combine into single transcript

### Important Implementation Details

- **25-second silence threshold**: Critical for audio splitting, do not change
- **FLAC optimization**: 16kHz mono for optimal transcription
- **Chunk metadata**: Preserved throughout pipeline for accurate timestamps
- **API key management**: Support both env vars and config file
- **Error handling**: Continue processing other files on failure

## Git Commit Guidelines

- Create meaningful commit messages explaining the "why"
- Focus on the purpose and impact of changes
- Use conventional commits when possible (feat:, fix:, docs:, etc.)
- Never include API keys or sensitive data

## Future Enhancements

The architecture is prepared for:
- REST API with FastAPI
- File monitoring service (watchdog)
- Mobile app integration
- WebSocket progress updates

These can be added without major refactoring due to the modular design.

## Testing Approach

- Unit tests for shared components
- Integration tests for full pipeline
- Mock external API calls in tests
- Test both success and failure scenarios
- Ensure consistent behavior

## Configuration Management

The platform uses a unified configuration system:
- Default config in `config/default.yaml`
- User config in `~/.config/neuravox/config.yaml`
- Environment variables for overrides
- API keys via env vars or config (env vars preferred)