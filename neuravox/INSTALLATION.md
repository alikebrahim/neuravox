# Neuravox Installation Guide

## Prerequisites

Before installing Neuravox, ensure you have:

1. **Python 3.12 or higher**
   ```bash
   python3 --version  # Should show 3.12+
   ```

2. **uv package manager**
   ```bash
   # Install uv if not present:
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **gum CLI tool**
   ```bash
   # Install gum if not present:
   go install github.com/charmbracelet/gum@latest
   # Or on macOS: brew install gum
   ```

4. **FFmpeg** (required for audio processing)
   ```bash
   # Ubuntu/Debian
   sudo apt install ffmpeg
   
   # Fedora
   sudo dnf install ffmpeg
   
   # macOS
   brew install ffmpeg
   ```

## Installation

1. **Clone the repository to ~/.neuravox**
   ```bash
   git clone <repository-url> ~/.neuravox
   cd ~/.neuravox
   ```

2. **Run the installer**
   ```bash
   ./scripts/install.sh
   ```

3. **Follow the installation prompts**
   - Choose "Install Neuravox" from the menu
   - The installer will:
     - Create a virtual environment with uv
     - Install all dependencies
     - Set up the neuravox command in ~/.local/bin
     - Initialize the workspace
     - Create selective symlinks for workspace directories
     - Install man pages

4. **Update your PATH** (if prompted)
   ```bash
   # For bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   
   # For zsh
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
   source ~/.zshrc
   ```

## Post-Installation

1. **Configure API keys** (for AI transcription)
   ```bash
   neuravox config
   ```
   
   Or set environment variables:
   ```bash
   export GOOGLE_API_KEY="your-google-api-key"
   export OPENAI_API_KEY="your-openai-api-key"
   ```

2. **Verify installation**
   ```bash
   neuravox --help
   man neuravox
   ```

## Usage

Place audio files in `~/neuravox.workspace/input/` and run:
```bash
neuravox process --interactive
```

## Workspace Structure

The installer creates workspace directories at:
- `~/neuravox.workspace/input/` - Place source audio files here
- `~/neuravox.workspace/processed/` - Split audio chunks
- `~/neuravox.workspace/transcribed/` - Final transcriptions

Note: Only these directories are symlinked to avoid database corruption. The SQLite state database remains in the main workspace.

## Updating

To update Neuravox:
```bash
cd ~/.neuravox
git pull
uv sync  # Update dependencies
```

## Uninstallation

To completely remove Neuravox:
```bash
cd ~/.neuravox
./scripts/install.sh
```
Then choose "Uninstall Neuravox" from the menu.

The uninstaller will:
- Remove the neuravox command
- Remove workspace symlinks
- Remove man pages
- Optionally remove configuration and installation directories

## Troubleshooting

### Command not found
Ensure `~/.local/bin` is in your PATH:
```bash
echo $PATH | grep -q "$HOME/.local/bin" && echo "PATH is OK" || echo "Need to add to PATH"
```

### Permission denied
Make sure the install script is executable:
```bash
chmod +x ~/.neuravox/scripts/install.sh
```

### Missing dependencies
The installer will check for all prerequisites and provide installation instructions if any are missing.

### Virtual environment issues
The launcher automatically uses the correct Python from the virtual environment. You don't need to activate it manually.