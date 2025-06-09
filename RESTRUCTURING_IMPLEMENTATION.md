# Neuravox Restructuring Implementation Plan

## Overview

This document contains the detailed implementation plan for restructuring Neuravox into a portable "clone-and-run" personal tool, based on the RESTRUCTURING.md plan with specific refinements.

## Implementation Phases

### Phase 0: Pre-restructuring Cleanup

1. **Add missing `__init__.py` files**:
   - `neuravox/modules/__init__.py`
   - `neuravox/modules/processor/__init__.py` (verify exists)
   - `neuravox/modules/transcriber/__init__.py` (verify exists)
   - `neuravox/modules/shared/__init__.py` (verify exists)

2. **Consolidate configuration systems**:
   - Remove duplicate `TranscriberConfig` from `modules/transcriber/config.py`
   - Update transcriber to use `UnifiedConfig` from `modules/shared/config.py`
   - Ensure all configuration is centralized

### Phase 1: Create New Structure and Entry Point

1. **Create `neuravox.py` at root**:
   ```python
   #!/usr/bin/env python3
   import sys
   from pathlib import Path
   
   # Add src directory to Python path
   sys.path.insert(0, str(Path(__file__).parent / "src"))
   
   # Import and run the CLI
   from neuravox.cli.main import app
   
   if __name__ == "__main__":
       app()
   ```

2. **Create directory structure**:
   - `src/neuravox/` (main package directory)
   - `src/neuravox/__init__.py`
   - `src/neuravox/__main__.py` (for `python -m neuravox`)

### Phase 2: Move and Reorganize Modules

Move files to new locations:
- `neuravox/cli/` → `neuravox/src/neuravox/cli/`
- `neuravox/core/` → `neuravox/src/neuravox/core/`
- `neuravox/modules/processor/` → `neuravox/src/neuravox/processor/`
- `neuravox/modules/transcriber/` → `neuravox/src/neuravox/transcriber/`
- `neuravox/modules/shared/` → `neuravox/src/neuravox/shared/`

### Phase 3: Update All Imports

Update imports throughout codebase:
- Change `from modules.shared.config import UnifiedConfig` to `from neuravox.shared.config import UnifiedConfig`
- Change `from modules.processor.audio_splitter import AudioProcessor` to `from neuravox.processor.audio_splitter import AudioProcessor`
- Change `from core.pipeline import AudioPipeline` to `from neuravox.core.pipeline import AudioPipeline`
- Remove all `sys.path` manipulations from existing code

### Phase 4: Create Setup Script and Launcher

1. **Create `scripts/setup.sh`**:
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

2. **Update `pyproject.toml`**:
   - Remove `[project.scripts]` entry points
   - Keep dependencies but remove build system requirements for editable installs

### Phase 5: Update Configuration

1. **Simplify config paths in `UnifiedConfig`**:
   - Remove multi-location searches
   - Use fixed paths: `~/.neuravox/config/`
   - Keep environment variable overrides

2. **Update workspace handling**:
   - Default workspace: `~/.neuravox/workspace/`
   - Environment override: `$NEURAVOX_WORKSPACE`

### Phase 6: Test and Update Documentation

1. **Test all functionality**:
   - Test `neuravox init`
   - Test `neuravox process`
   - Test transcription features
   - Verify imports work correctly

2. **Update documentation**:
   - Update `INSTALLATION.md` with new setup instructions
   - Update `README.md` with new structure
   - Update `CLAUDE.md` with new development workflow

## Implementation Order

1. Start with Phase 0 (cleanup) to ensure clean base
2. Create new structure (Phase 1-2) without breaking existing code
3. Update imports (Phase 3) - this is the breaking change
4. Create setup infrastructure (Phase 4-5)
5. Test thoroughly and update docs (Phase 6)

## Key Technical Details

### Import Path Strategy

The `neuravox.py` entry point will properly set up the Python path:
```python
sys.path.insert(0, str(Path(__file__).parent / "src"))
```

This allows all imports to work as `from neuravox.module import ...` without requiring installation.

### Configuration Consolidation

The current dual configuration system will be unified:
- Remove `TranscriberConfig` class
- Use only `UnifiedConfig` for all configuration needs
- Centralize all config logic in `neuravox/shared/config.py`

### Gradual Migration

The implementation maintains functionality during most phases:
- Phases 0-2: Existing code continues to work
- Phase 3: Breaking change when imports are updated
- Phases 4-6: New structure is finalized and tested

This approach minimizes risk and allows for incremental testing throughout the restructuring process.