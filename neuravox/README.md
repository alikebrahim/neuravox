# Neuravox

Personal neural audio processing and transcription tool

## Overview

Neuravox is a personal tool for processing and transcribing audio files. It combines intelligent audio splitting based on silence detection with multi-model AI transcription capabilities. Designed as a "clone-and-run" tool that lives in `~/.neuravox`.

## Features

- **Intelligent Audio Processing**
  - Automatic silence detection (25+ second gaps)
  - Audio optimization (FLAC format at 16kHz mono)
  - Batch processing with metadata tracking
  - Smart chunk creation for optimal transcription

- **Multi-Model Transcription**
  - Google Gemini Flash support
  - OpenAI Whisper API integration
  - Local Whisper models (offline transcription)
  - Chunk-aware processing with timing preservation

- **Unified Pipeline**
  - Seamless processing from input to transcript
  - State management with resume capability
  - Progress tracking and error recovery
  - Rich CLI interface

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://astral.sh/uv) package manager
- FFmpeg for audio processing
- Linux operating system

### Installation

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone to the required location
git clone <repository-url> ~/.neuravox

# Run setup
cd ~/.neuravox
./scripts/setup.sh

# Add to PATH if needed
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Usage

```bash
# Initialize workspace
neuravox init

# Place audio files in ~/neuravox.workspace/input/
# Then process interactively
neuravox process --interactive

# Check processing status
neuravox status

# Resume failed jobs
neuravox resume
```

## Workspace Structure

Your workspace at `~/neuravox.workspace/`:

```
~/neuravox.workspace/
├── input/        # Place audio files here
├── processed/    # Split audio chunks
└── transcribed/  # Transcription results
```

## Configuration

### API Keys

Set environment variables:
```bash
export GOOGLE_API_KEY="your-key"
export OPENAI_API_KEY="your-key"
```

Or create `~/.neuravox/config/user.yaml`:
```yaml
api_keys:
  google_gemini: "your-key"
  openai: "your-key"
```

### Workspace Override

```bash
export NEURAVOX_WORKSPACE="/custom/path"
```

## Updating

```bash
cd ~/.neuravox
git pull
uv sync  # Update dependencies if needed
```

## Architecture

Neuravox uses a modular architecture:

- **Processor Module**: Handles audio splitting and optimization
- **Transcriber Module**: Manages AI model interactions
- **Core Pipeline**: Orchestrates the full workflow
- **Shared Utilities**: Common functionality across modules

## Development

For development work, clone to a different location:

```bash
git clone <repository-url> ~/dev/neuravox
cd ~/dev/neuravox
uv venv && source .venv/bin/activate
uv sync
python neuravox.py --help
```

## License

MIT License - See LICENSE file for details