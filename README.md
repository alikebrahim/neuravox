# Neuravox

Audio processing and transcription tool

## Overview

Audio processing wrapper around FFmpeg and transcription APIs. Splits audio on silence and transcribes using various models (OpenAI, Google, local Whisper). Designed as a "clone-and-run" tool that lives in `~/.neuravox`.

## Features

- **Audio Processing**
  - Silence detection and splitting (25+ second gaps)
  - FLAC format conversion at 16kHz mono
  - Batch processing with metadata tracking

- **Transcription**
  - Google Gemini Flash
  - OpenAI Whisper API
  - Local Whisper models (offline)
  - Timing preservation

- **Pipeline**
  - State management with resume capability
  - Progress tracking and error recovery
  - CLI interface

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://astral.sh/uv)
- FFmpeg
- Linux

### Installation

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install  
git clone <repository-url> ~/.neuravox
cd ~/.neuravox
uv sync
./scripts/install.sh

# Add to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Usage

```bash
# Initialize workspace
neuravox init

# Place audio files in ~/neuravox.workspace/input/
# Process interactively
neuravox process -i

# Full pipeline  
neuravox pipeline -i

# Commands
neuravox process    # Audio processing only
neuravox transcribe # Transcription only
neuravox convert    # Format conversion
neuravox status     # Check status
neuravox resume     # Resume failed jobs
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

```bash
export GOOGLE_API_KEY="your-key"
export OPENAI_API_KEY="your-key"
```

Or edit `~/.neuravox/.env`:
```
GOOGLE_API_KEY=your-key
OPENAI_API_KEY=your-key
```

### Workspace Override

```bash
export NEURAVOX_WORKSPACE="/custom/path"
```

## Updating

```bash
cd ~/.neuravox
git pull
uv sync
```

## Development

```bash
git clone <repository-url> ~/dev/neuravox
cd ~/dev/neuravox
uv sync
python neuravox.py --help
```

## License

MIT License - See LICENSE file for details