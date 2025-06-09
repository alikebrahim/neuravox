# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Neuravox is a unified platform for neural audio processing and transcription that combines:

1. **Audio Processing**: Sophisticated audio splitting tool that detects silence gaps (25+ seconds) and splits audio files for optimal transcription
2. **AI Transcription**: Modular transcription engine using various AI models (Google Gemini, OpenAI Whisper API, Local Whisper)

The platform is integrated in the `neuravox` directory with a unified CLI command: `neuravox`

## Common Development Commands

### Using Neuravox
```bash
# From the project root
cd neuravox

# Set up development environment
uv venv
source .venv/bin/activate
uv sync

# Run from source
python neuravox.py --help

# Initialize workspace
python neuravox.py init

# Process and transcribe audio
python neuravox.py process --interactive

# Check status
python neuravox.py status

# Resume failed jobs
python neuravox.py resume
```

### For installed version (after setup.sh)
```bash
# Initialize workspace
neuravox init

# Process and transcribe in one workflow
neuravox process --interactive

# Check processing status
neuravox status

# Resume any failed jobs
neuravox resume
```

## Architecture & Key Components

### Project Structure
```
neuravox/
├── neuravox.py           # Main entry point
├── src/neuravox/         # Source code
│   ├── cli/              # CLI interface
│   ├── core/             # Pipeline orchestration
│   ├── processor/        # Audio processing
│   ├── transcriber/      # Transcription engine
│   └── shared/           # Shared utilities
├── config/               # Default configuration
├── scripts/              # Setup and utility scripts
└── workspace/            # User data (symlinked to ~/neuravox.workspace)
```

### Audio Processing
- **Core Logic**: `src/neuravox/processor/audio_splitter.py` - handles silence detection and splitting
- **Key Algorithm**: 25-second silence detection threshold (preserve this in any modifications)
- **Output Format**: FLAC files optimized at 16kHz mono for transcription
- **Metadata**: Generates JSON/CSV with chunk timings and statistics

### AI Transcription
- **Engine**: `src/neuravox/transcriber/engine.py` - manages transcription workflow
- **Model Architecture**: Pluggable model system in `src/neuravox/transcriber/models/` with base class and provider implementations
- **Configuration**: System prompts in `config/prompts.toml`
- **Project Organization**: All outputs organized by project name

### Integration Architecture
The unified platform provides:
- Seamless pipeline from audio input to transcription output
- Shared configuration and workspace management
- Consistent metadata handling across processing stages
- State management for reliability and resume capability

## Important Development Notes

### Git Commit Guidelines
- Create meaningful, concise commit messages explaining the "why" not just the "what"
- Focus on the purpose and impact of changes
- Avoid generic messages like "Update" or "Fix" without context
- Never include Claude signatures in commits

### Module-Specific Considerations

**Audio Processing**:
- The 25-second silence detection is calibrated for specific use cases - maintain this threshold
- FLAC optimization settings (16kHz, mono) are chosen for speech transcription compatibility
- File organization (moving to processed/) helps manage large batches

**AI Transcription**:
- Model selection affects both speed and quality - Google Gemini is currently most reliable
- System prompts in `config/prompts.toml` can be customized per project needs
- Project-based organization allows parallel transcription workflows

### Testing
```bash
# Run all tests
cd neuravox
pytest

# Run specific test modules
pytest tests/unit/test_config.py
pytest tests/integration/test_pipeline.py

# Run with coverage
pytest --cov=src/neuravox
```

### Linting and Formatting
```bash
# Check code style
ruff check .

# Format code
ruff format .
```