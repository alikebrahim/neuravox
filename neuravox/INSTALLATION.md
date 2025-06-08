# Neuravox Installation Guide

## Overview

Neuravox is a standalone neural audio processing and transcription platform. This guide covers the complete installation process, environment setup, and data initialization.

## System Requirements

- **Python**: 3.12 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: 4GB RAM minimum (8GB recommended for large files)
- **Storage**: 10GB free space for workspace and dependencies
- **Audio Dependencies**: FFmpeg (required for audio processing and Whisper)
  - Linux: `sudo apt install ffmpeg`
  - macOS: `brew install ffmpeg`
  - Windows: Automatically handled by ffmpeg-python package

## Virtual Environment Handling

When you run `neuravox` from the command line, the virtual environment is handled differently depending on your installation method:

### Method 1: Quick Install with pipx (Simplest)
```bash
./scripts/quick-install.sh
```
- **One command installation** - handles everything
- **Automatic venv management** - pipx creates and manages the venv
- **No manual activation needed** - just run `neuravox`
- **Isolated from system Python** - no conflicts
- **Easy updates**: `pipx upgrade neuravox`

### Method 2: Interactive Installation (Recommended)
```bash
./scripts/install-system.sh
```
- **Modern TUI installer** - uses Gum/whiptail for beautiful menus
- **Auto-detects your shell** - configures .bashrc or .zshrc automatically
- **Prefers uv** - uses fast uv package manager, falls back to pip
- **Choose installation type**:
  - User Install (~/.neuravox) - Recommended
  - System Install (/opt/neuravox) - Requires sudo
  - Development Mode - For contributors
- **Creates wrapper script** - no manual venv activation needed

### Method 3: Development Installation
```bash
cd neuravox
uv venv
source .venv/bin/activate
uv pip install -e .
```
- **Requires manual activation** each time
- **Best for development** and testing
- **Editable installation** - changes take effect immediately

### Method 4: Direct pip Install
```bash
# Not recommended - installs to active environment
pip install neuravox
```
- **No automatic venv** - uses current environment
- **Risk of conflicts** with system packages
- **Requires manual venv management**

## Installation Strategy

### 1. Project Structure

```
neuravox/
├── .venv/                 # Virtual environment (created during install)
├── modules/               # Core functionality
├── cli/                   # Command-line interface
├── core/                  # Business logic and state management
├── config/                # Default configurations
├── tests/                 # Test suite
└── pyproject.toml         # Unified dependency management
```

### 2. Virtual Environment Management

Neuravox uses `uv` for fast, reliable virtual environment management:

```bash
# Option A: Using uv (recommended)
cd neuravox
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Option B: Using standard venv
cd neuravox
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### 3. Installation Process

#### Step 1: Clone or Download
```bash
# If using git
git clone <repository-url>
cd neuravox

# Or download and extract the archive
unzip neuravox.zip
cd neuravox
```

#### Step 2: Create Virtual Environment
```bash
# Using uv (faster)
uv venv
source .venv/bin/activate

# Or using standard Python
python3.12 -m venv .venv
source .venv/bin/activate
```

#### Step 3: Install Dependencies
```bash
# Editable install for development
uv pip install -e .

# Or for production use
uv pip install .
```

#### Step 4: Initialize Workspace
```bash
neuravox init
```

## Data Initialization

### SQLite Database

The platform uses SQLite for state management, which is automatically initialized:

**Location**: `~/neuravox/.pipeline_state.db`

**Schema**:
- `files`: Track processed files and their status
- `processing_stages`: Record processing history
- `chunks`: Store audio chunk metadata

**Initialization**: Automatic on first use when you run `neuravox init`

### Workspace Structure

The default workspace is created at `~/neuravox/` with:

```
~/neuravox/
├── .pipeline_state.db     # SQLite database (auto-created)
├── .neuravox.yaml        # User configuration (created on init)
├── input/                # Place audio files here
├── processed/            # Original files moved here after processing
├── output/               # Processing results
│   └── <project-name>/
│       ├── chunks/       # Audio chunks
│       ├── transcripts/  # Individual transcriptions
│       └── metadata/     # Processing metadata
└── logs/                 # Application logs
```

### Configuration Files

1. **User Config**: `~/.config/neuravox/config.yaml`
   - Created on first run
   - Stores user preferences
   - Overrides defaults

2. **Environment File**: `.env` (in project root)
   - API keys and secrets
   - Never committed to version control

3. **Default Config**: `config/default.yaml`
   - Ships with the platform
   - Reference configuration

## API Key Configuration

### Method 1: Environment Variables
```bash
export GOOGLE_API_KEY="your-google-api-key"
export OPENAI_API_KEY="your-openai-api-key"
```

### Method 2: .env File
```bash
# Create .env in project root
echo "GOOGLE_API_KEY=your-google-api-key" >> .env
echo "OPENAI_API_KEY=your-openai-api-key" >> .env
```

### Method 3: Interactive Setup
```bash
neuravox config
# Follow prompts to enter API keys
```

## Installation Verification

### 1. Check Installation
```bash
# Verify command is available
neuravox --version

# Check configuration
neuravox config --show
```

### 2. Run Tests
```bash
# Run unit tests
pytest tests/unit

# Run integration tests (requires API keys)
pytest tests/integration
```

### 3. Process Test Audio
```bash
# Download test audio
wget https://example.com/sample-audio.mp3 -O ~/neuravox/input/test.mp3

# Process interactively
neuravox process --interactive
```

## Dependency Management

All dependencies are managed through a single `pyproject.toml`:

**Core Dependencies**:
- Audio Processing: librosa, soundfile, scipy, numpy
- AI/ML: google-genai, openai, ollama
- CLI: typer[all], rich, tqdm
- Data: pydantic, sqlalchemy
- Utils: pyyaml, toml, python-dotenv

**Development Dependencies**:
- Testing: pytest, pytest-asyncio
- Linting: ruff
- Type Checking: mypy (optional)

## Platform-Specific Notes

### Linux
- FFmpeg usually available via package manager
- Use system Python 3.12+ or pyenv

### macOS
- Install FFmpeg via Homebrew: `brew install ffmpeg`
- Python 3.12 via Homebrew or pyenv

### Windows
- FFmpeg binaries included via ffmpeg-python
- Use Python from python.org or Microsoft Store

## Troubleshooting

### Common Issues

1. **Missing Python 3.12**
   ```bash
   # Install via pyenv
   pyenv install 3.12
   pyenv local 3.12
   ```

2. **FFmpeg Not Found**
   ```bash
   # Linux
   sudo apt-get install ffmpeg
   
   # macOS
   brew install ffmpeg
   
   # Windows - handled automatically
   ```

3. **Permission Errors**
   ```bash
   # Ensure workspace is writable
   chmod -R u+w ~/neuravox
   ```

4. **Database Lock Errors**
   - Close other instances of Neuravox
   - Check file permissions on `.pipeline_state.db`

## Uninstallation

### Complete Removal
```bash
# Remove virtual environment
rm -rf .venv

# Remove workspace (caution: deletes all data)
rm -rf ~/neuravox

# Remove user config
rm -rf ~/.config/neuravox

# Uninstall command (if installed globally)
pip uninstall neuravox
```

### Keep Data, Remove Installation
```bash
# Just remove virtual environment
rm -rf .venv

# Keep workspace and database intact
```

## Next Steps

1. **Configure API Keys**: Set up at least one transcription model
2. **Test Installation**: Run `neuravox process --help`
3. **Process First Audio**: Try interactive mode with `neuravox process --interactive`
4. **Explore Features**: Check available models with `neuravox list-models`

For more information, see the main README.md or run `neuravox --help`.