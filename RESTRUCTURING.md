# Neuravox Project Restructuring Plan

## Status: ✅ IMPLEMENTED

This restructuring has been successfully implemented. See RESTRUCTURING_IMPLEMENTATION.md for the detailed implementation steps that were followed.

## Overview

This document outlines a comprehensive restructuring plan to transform Neuravox into a portable, "clone-and-run" personal tool. The goal is to simplify the installation by cloning to `~/.neuravox`, using `uv sync` for dependencies, and providing a simple launcher script.

## Objectives

1. **Simple Installation**: Clone to `~/.neuravox` and run setup script
2. **Simple Updates**: Update via `git pull` and `uv sync` if needed
3. **Clear Separation**: Distinct boundaries between code, configuration, and user data
4. **Personal Tool Focus**: Optimized for single-user personal use
5. **No Complex Entry Points**: Simple bash launcher through venv

## Current Issues

- Requires `pip install -e .` for proper installation
- Uses absolute imports that break portability
- Configuration searches multiple system locations
- Entry points depend on pip installation
- No clear separation between code and user data

## Proposed Structure

### Directory Layout

```
neuravox/                    # Cloned to ~/.neuravox
├── neuravox.py              # Main Python entry point
├── neuravox                 # Unix shell script launcher
├── pyproject.toml           # Dependencies for uv sync
├── scripts/                 # Setup and utility scripts
│   └── setup.sh            # Initial setup script
├── src/                     # All source code
│   ├── __init__.py
│   ├── neuravox/           # Main package
│   │   ├── __init__.py
│   │   ├── __main__.py     # Allow: python -m neuravox
│   │   ├── cli/            # CLI interface (from current cli/)
│   │   ├── core/           # Core logic (from current core/)
│   │   ├── processor/      # Audio processing (from modules/processor/)
│   │   ├── transcriber/    # Transcription (from modules/transcriber/)
│   │   └── shared/         # Shared utilities (from modules/shared/)
├── config/                  # Default configurations
│   ├── default.yaml
│   └── prompts.toml
├── workspace/               # Workspace directory (symlinked to ~/neuravox.workspace)
│   ├── input/
│   ├── processed/
│   └── transcribed/
├── docs/                    # Documentation
│   └── man/                # Man pages
├── tests/                   # Test suite
├── .gitignore              # Updated for new structure
├── README.md
├── INSTALLATION.md         # Updated installation instructions
└── CLAUDE.md               # AI assistance guide
```

## Key Changes

### 1. Installation and Setup

The setup process follows a simple pattern:

- Clone repository to `~/.neuravox`
- Run `scripts/setup.sh` which:
  - Uses `uv sync` to create `.venv` and install dependencies
  - Ensures `~/.local/bin` is in PATH
  - Creates launcher script at `~/.local/bin/neuravox`
  - Creates symlink `~/neuravox.workspace` → `~/.neuravox/workspace/`

### 2. Launcher Script

The launcher at `~/.local/bin/neuravox` will:

```bash
#!/usr/bin/env bash
exec "$HOME/.neuravox/.venv/bin/python" "$HOME/.neuravox/neuravox.py" "$@"
```

### 3. Import Strategy

Keep imports simple since we're running from a fixed location (`~/.neuravox`):

```python
# Simple imports work fine with proper PYTHONPATH setup
from neuravox.processor.audio_splitter import AudioProcessor
from neuravox.shared.config import UnifiedConfig
```

### 4. Configuration Management

Simplified configuration for personal use:

```python
# Configuration search order:
1. $NEURAVOX_CONFIG (if set)
2. ~/.neuravox/config/user.yaml (user overrides)
3. ~/.neuravox/config/default.yaml (defaults)
```

### 5. Workspace Management

Single workspace location with symlink:

- Actual location: `~/.neuravox/workspace/`
- User access via: `~/neuravox.workspace` (symlink)
- Override with: `$NEURAVOX_WORKSPACE` environment variable

### 6. Dependency Management

Use `pyproject.toml` with `uv`:

- Single source of truth for dependencies
- Fast installation with `uv sync`
- No need for multiple requirements files for personal use

## Implementation Plan

### Phase 1: Structure Simplification

1. Create simple `neuravox.py` entry point at root
2. Move current modules to new structure:
   - `cli/` → `src/neuravox/cli/`
   - `core/` → `src/neuravox/core/`
   - `modules/processor/` → `src/neuravox/processor/`
   - `modules/transcriber/` → `src/neuravox/transcriber/`
   - `modules/shared/` → `src/neuravox/shared/`
3. Update imports to work with new paths
4. Remove complex entry point configurations from pyproject.toml

### Phase 2: Setup Script Creation

1. Create `scripts/setup.sh` that:
   - Checks for `uv` installation
   - Runs `uv sync` to create `.venv`
   - Creates launcher at `~/.local/bin/neuravox`
   - Creates workspace symlink
   - Checks PATH configuration

### Phase 3: Configuration Updates

1. Simplify configuration to single user model
2. Remove multi-location search paths
3. Set up workspace symlink handling
4. Update config loading to use simple console logging only

### Phase 4: Testing & Documentation

1. Test installation process
2. Test updates via `git pull`
3. Update documentation for new setup
4. Remove all platform-specific considerations except Linux

## Benefits

### Personal Tool Advantages

- Simple clone to `~/.neuravox` and run setup
- No complex installation procedures
- Easy updates with `git pull`
- All data in one place with convenient symlink
- No system-wide changes except PATH addition
- Clear separation of code and workspace data

## Installation Guide

### Fresh Installation

1. **Clone repository**:

   ```bash
   git clone <repository-url> ~/.neuravox
   cd ~/.neuravox
   ```

2. **Run setup**:

   ```bash
   ./scripts/setup.sh
   ```

3. **Add PATH if needed**:

   ```bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```

4. **Start using**:

   ```bash
   neuravox --help
   ```


## Update Mechanism

### Simple Updates

```bash
cd ~/.neuravox
git pull

# If dependencies changed (pyproject.toml modified):
uv sync
```

That's it! No complex update procedures needed.

## Compatibility

### Workspace Compatibility

- Existing workspace data remains compatible
- Simple copy to new location
- API keys via environment variables still work

### Platform Support

- **Linux**: Only supported platform (personal tool)

## Setup Script Details

The `scripts/setup.sh` will:

```bash
#!/usr/bin/env bash
set -e

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "Error: uv not found. Install from: https://astral.sh/uv"
    exit 1
fi

# Create venv and install deps
cd ~/.neuravox
uv sync

# Create launcher
mkdir -p ~/.local/bin
cat > ~/.local/bin/neuravox << 'EOF'
#!/usr/bin/env bash
exec "$HOME/.neuravox/.venv/bin/python" "$HOME/.neuravox/neuravox.py" "$@"
EOF
chmod +x ~/.local/bin/neuravox

# Create workspace symlink
ln -sf ~/.neuravox/workspace ~/neuravox.workspace

# Check PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "Add to PATH: export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo "Setup complete!"
```

## Decision Points and Recommendations

### Confirmed Implementation Choices

Based on notes and requirements:

1. **Python Entry Point Structure**: Simple `neuravox.py` at root with `sys.path` manipulation
2. **Dependency Management**: Keep `pyproject.toml` for uv sync
3. **Configuration Format**: Keep YAML for configuration files
4. **Logging Strategy**: Simple console output only - no file logging

### Best Practices for Personal Tool

1. **Keep It Simple**: No need for complex multi-user features
2. **Fixed Paths**: Using `~/.neuravox` simplifies many things
3. **Single Workspace**: One workspace with convenient symlink is enough
4. **Minimal Config**: Don't over-engineer configuration for personal use
5. **Direct Execution**: Simple bash launcher is more maintainable than complex entry points

## Summary of Key Changes

1. **Installation**: Clone to `~/.neuravox` (not ~/apps/neuravox or other locations)
2. **Dependencies**: Use `uv sync` instead of pip install
3. **Launcher**: Simple bash script executing through venv
4. **Entry Point**: Simple `neuravox.py` at root with sys.path setup
5. **Workspace**: Symlink at ~/neuravox.workspace pointing to ~/.neuravox/workspace
6. **Platform**: Linux-only personal tool
7. **Logging**: Console output only, no file logging
8. **Updates**: Simple `git pull` and `uv sync` when needed

## Next Steps

1. Begin Phase 1: Structure simplification
2. Create the simple entry point script
3. Reorganize modules into src/neuravox/
4. Create and test setup.sh script
5. Update documentation
