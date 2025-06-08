# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Neuravox is a unified platform that combines two powerful modules for neural audio processing:

1. **audio_processor**: Sophisticated audio splitting tool that detects silence gaps (25+ seconds) and splits audio files for optimal transcription
2. **ai_transcriber**: Modular CLI tool for transcribing audio using various AI models (Google Gemini, OpenAI Whisper, Ollama)

The platform is integrated in the `neuravox` directory with a unified CLI command: `neuravox`

## Common Development Commands

### Audio Processor Module
```bash
cd audio_processor

# Install dependencies
uv sync

# Run interactive processing (recommended)
uv run python audio_splitter_cli.py process --interactive

# Run batch processing with default settings
uv run python audio_splitter_cli.py process

# Process without moving files
uv run python audio_splitter_cli.py process --no-move

# Optimize single file
uv run python audio_splitter_cli.py optimize input.wav -o output.flac
```

### AI Transcriber Module
```bash
cd ai_transcriber

# Install as package
pip install -e .

# Run interactive transcription (recommended)
audio-transcriber interactive

# Direct transcription
audio-transcriber transcribe audio.mp3 --model google-gemini --project "project-name"

# List available models
audio-transcriber list-models
```

### Integrated Workflow (Recommended)
```bash
# Using the unified Neuravox platform
cd neuravox
uv pip install -e .

# Initialize workspace
neuravox init

# Process and transcribe in one workflow
neuravox process --interactive
```

### Legacy Module Usage
The original modules can still be used independently as shown above.

## Architecture & Integration Points

### Audio Processor
- **Entry Point**: `audio_splitter_cli.py` (modern CLI) or `run.py` (simple batch)
- **Core Logic**: `audio_splitter.py` - handles silence detection and splitting
- **Key Algorithm**: 25-second silence detection threshold (preserve this in any modifications)
- **Output Format**: FLAC files optimized at 16kHz mono for transcription
- **Metadata**: Generates JSON/CSV with chunk timings and statistics

### AI Transcriber
- **Entry Point**: `src/cli.py` via `audio-transcriber` command
- **Model Architecture**: Pluggable model system in `src/models/` with base class and provider implementations
- **Configuration**: System prompts in `config/prompts.toml`
- **Project Organization**: All outputs organized by project name

### Integration Architecture
Both modules share:
- Similar directory structures (`input/`, `output/`)
- Comprehensive metadata generation
- Compatible audio formats (audio_processor outputs FLAC that transcriber handles well)

Key integration points:
1. Audio processor's output directory can be directly used as transcriber's input
2. Chunk metadata from processor can inform transcription organization
3. Both support batch processing for workflow automation

## Important Development Notes

### Git Commit Guidelines
- Create meaningful, concise commit messages explaining the "why" not just the "what"
- Focus on the purpose and impact of changes
- Avoid generic messages like "Update" or "Fix" without context
- Never include Claude signatures in commits

### Module-Specific Considerations

**Audio Processor**:
- The 25-second silence detection is calibrated for specific use cases - maintain this threshold
- FLAC optimization settings (16kHz, mono) are chosen for speech transcription compatibility
- File organization (moving to processed/) helps manage large batches

**AI Transcriber**:
- Model selection affects both speed and quality - Google Gemini is currently most reliable
- System prompts in `config/prompts.toml` can be customized per project needs
- Project-based organization allows parallel transcription workflows

### Future Integration Opportunities
1. Create a unified CLI that chains both operations
2. Pass chunk metadata from processor to transcriber for enhanced organization
3. Implement shared configuration for common settings
4. Add progress tracking across the full pipeline