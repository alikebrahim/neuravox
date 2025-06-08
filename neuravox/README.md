# Neuravox

Neural audio processing and transcription platform

## Overview

Neuravox is a comprehensive platform for processing and transcribing audio files. It combines intelligent audio splitting based on silence detection with multi-model AI transcription capabilities.

## Features

- **Intelligent Audio Processing**
  - Automatic silence detection (25+ second gaps)
  - Audio optimization (FLAC format at 16kHz mono)
  - Batch processing with metadata tracking
  - Smart chunk creation for optimal transcription

- **Multi-Model Transcription**
  - Google Gemini Flash support
  - OpenAI Whisper integration
  - Local Ollama models
  - Chunk-aware processing with timing preservation

- **Unified Pipeline**
  - Seamless processing from input to transcript
  - State management with resume capability
  - Progress tracking and error recovery
  - Rich CLI interface

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd neuravox

# Create virtual environment and install
uv venv
source .venv/bin/activate
uv pip install -e .

# Initialize workspace
neuravox init
```

## Quick Start

### Interactive Mode (Recommended)
```bash
neuravox process --interactive
```

### Direct Processing
```bash
# Process specific files
neuravox process audio1.mp3 audio2.wav

# Process with specific model
neuravox process audio.mp3 --model google-gemini

# Check processing status
neuravox status

# Resume failed jobs
neuravox resume
```

## Configuration

Neuravox uses a hierarchical configuration system:
1. Environment variables (highest priority)
2. User config file (`~/.config/neuravox/config.yaml`)
3. Default configuration

### Setting API Keys

```bash
# Via environment variables
export GOOGLE_API_KEY="your-key"
export OPENAI_API_KEY="your-key"

# Or in .env file
cp .env.example .env
# Edit .env with your keys
```

### View/Edit Configuration

```bash
neuravox config
```

## Workflow

1. **Initialize**: Set up your workspace and configuration
2. **Process**: Audio files are analyzed and split at silence gaps
3. **Transcribe**: Each chunk is transcribed using your chosen AI model
4. **Combine**: Chunks are merged into a complete transcript with timing

## Output Structure

```
workspace/
├── input/          # Place audio files here
├── output/         # Processed results
│   └── <project>/
│       ├── chunks/     # Audio chunks
│       ├── transcripts/# Individual transcriptions
│       ├── combined_transcript.md
│       └── metadata.json
└── processed/      # Original files moved here
```

## Models

### Google Gemini (Recommended)
- Fast and accurate
- Good for long audio files
- Requires Google API key

### OpenAI Whisper
- High accuracy
- Multiple model sizes
- Requires OpenAI API key

### Ollama (Local)
- Privacy-focused
- No API key required
- Requires Ollama installation

## Development

```bash
# Run tests
pytest

# Lint code
ruff check .

# Format code
ruff format .
```

## License

MIT License - see LICENSE file for details