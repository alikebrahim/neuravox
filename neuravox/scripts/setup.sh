#!/usr/bin/env bash
set -e

# Neuravox Setup Script
# This script sets up Neuravox as a personal tool in ~/.neuravox

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "==================================="
echo "  Neuravox Setup Script"
echo "==================================="
echo

# Check if we're in the right directory
if [[ ! -f "$PROJECT_ROOT/neuravox.py" ]]; then
    echo "Error: This script must be run from the neuravox directory"
    echo "Please run: ./scripts/setup.sh"
    exit 1
fi

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "Error: uv not found. Install from: https://astral.sh/uv"
    echo "Quick install: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if already at ~/.neuravox
if [[ "$PROJECT_ROOT" != "$HOME/.neuravox" ]]; then
    echo "This script expects the project to be cloned to ~/.neuravox"
    echo "Current location: $PROJECT_ROOT"
    echo
    read -p "Move project to ~/.neuravox? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [[ -d "$HOME/.neuravox" ]]; then
            echo "Error: ~/.neuravox already exists"
            exit 1
        fi
        echo "Moving project to ~/.neuravox..."
        mv "$PROJECT_ROOT" "$HOME/.neuravox"
        cd "$HOME/.neuravox"
        PROJECT_ROOT="$HOME/.neuravox"
    else
        echo "Setup cancelled. Please clone to ~/.neuravox and run setup again."
        exit 1
    fi
fi

echo "Setting up Neuravox in: $PROJECT_ROOT"
echo

# Create venv and install dependencies
echo "Creating virtual environment and installing dependencies..."
cd "$PROJECT_ROOT"
uv sync

echo
echo "Creating launcher script..."

# Create launcher
mkdir -p ~/.local/bin
cat > ~/.local/bin/neuravox << 'EOF'
#!/usr/bin/env bash
exec "$HOME/.neuravox/.venv/bin/python" "$HOME/.neuravox/neuravox.py" "$@"
EOF
chmod +x ~/.local/bin/neuravox

echo "Creating workspace symlink..."

# Create workspace directory if it doesn't exist
mkdir -p ~/.neuravox/workspace/{input,processed,transcribed}

# Create workspace symlink
if [[ -L ~/neuravox.workspace ]]; then
    echo "Workspace symlink already exists at ~/neuravox.workspace"
elif [[ -e ~/neuravox.workspace ]]; then
    echo "Warning: ~/neuravox.workspace exists but is not a symlink"
    echo "Please remove it manually if you want to create the symlink"
else
    ln -sf ~/.neuravox/workspace ~/neuravox.workspace
    echo "Created symlink: ~/neuravox.workspace -> ~/.neuravox/workspace"
fi

echo
echo "Checking PATH configuration..."

# Check PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "WARNING: ~/.local/bin is not in your PATH"
    echo
    echo "Add this line to your shell configuration file (~/.bashrc, ~/.zshrc, etc.):"
    echo '    export PATH="$HOME/.local/bin:$PATH"'
    echo
    echo "Then reload your shell or run: source ~/.bashrc"
else
    echo "✓ PATH is correctly configured"
fi

echo
echo "==================================="
echo "  Setup Complete!"
echo "==================================="
echo
echo "Neuravox has been installed to: ~/.neuravox"
echo "Workspace is available at: ~/neuravox.workspace"
echo
echo "To get started:"
echo "  neuravox init        # Initialize workspace"
echo "  neuravox --help      # Show help"
echo
echo "Place audio files in: ~/neuravox.workspace/input/"
echo "Then run: neuravox process --interactive"
echo