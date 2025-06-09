# Neuravox Installation Guide

## Overview

Neuravox is a personal neural audio processing and transcription tool designed to be cloned and run from `~/.neuravox`. This guide covers the simple installation process.

## System Requirements

- **Python**: 3.12 or higher
- **Operating System**: Linux (primary support)
- **Memory**: 4GB RAM minimum (8GB recommended for large files)
- **Storage**: 10GB free space for workspace and dependencies
- **Package Manager**: [uv](https://astral.sh/uv) (required)
- **Audio Dependencies**: FFmpeg (required for audio processing)
  - Linux: `sudo apt install ffmpeg` or `sudo dnf install ffmpeg`

## Installation

### 1. Install Prerequisites

First, install `uv` if you don't have it:

```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install FFmpeg:

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch
sudo pacman -S ffmpeg
```

### 2. Clone and Setup

```bash
# Clone to the required location
git clone <repository-url> ~/.neuravox

# Run setup
cd ~/.neuravox
./scripts/setup.sh
```

The setup script will:
- Create a virtual environment using `uv`
- Install all dependencies
- Create a launcher at `~/.local/bin/neuravox`
- Create workspace symlink at `~/neuravox.workspace`

### 3. Configure PATH

If `~/.local/bin` is not in your PATH, add it:

```bash
# For bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# For zsh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### 4. Configure API Keys (Optional)

For AI transcription features, set your API keys:

```bash
# Add to your shell configuration
export GOOGLE_API_KEY="your-google-api-key"
export OPENAI_API_KEY="your-openai-api-key"
```

Or create `~/.neuravox/config/user.yaml`:

```yaml
api_keys:
  google_gemini: "your-google-api-key"
  openai: "your-openai-api-key"
```

## Usage

### Initialize Workspace

```bash
neuravox init
```

### Process Audio Files

1. Place audio files in: `~/neuravox.workspace/input/`
2. Run interactive processing:

```bash
neuravox process --interactive
```

### Check Status

```bash
neuravox status
```

## Updating

To update Neuravox:

```bash
cd ~/.neuravox
git pull

# Update dependencies if needed
uv sync
```

## Workspace Structure

Your workspace at `~/neuravox.workspace/` contains:

```
~/neuravox.workspace/
├── input/        # Place audio files here
├── processed/    # Split audio chunks
└── transcribed/  # Transcription results
```

## Troubleshooting

### Command not found

Make sure `~/.local/bin` is in your PATH:

```bash
echo $PATH | grep -q "$HOME/.local/bin" && echo "PATH is OK" || echo "Need to add to PATH"
```

### Permission denied

Make sure the launcher is executable:

```bash
chmod +x ~/.local/bin/neuravox
```

### Virtual environment issues

The launcher automatically uses the correct Python from the virtual environment. You don't need to activate it manually.

## Uninstallation

To completely remove Neuravox:

```bash
# Remove the installation
rm -rf ~/.neuravox

# Remove the launcher
rm -f ~/.local/bin/neuravox

# Remove the workspace symlink
rm -f ~/neuravox.workspace

# Optionally remove workspace data
rm -rf ~/.neuravox/workspace
```