#!/usr/bin/env bash
# Neuravox launcher script - automatically handles virtual environment

# Find the installation directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check if we're in development mode (has .venv) or installed mode
if [ -d "$PROJECT_ROOT/.venv" ]; then
    # Development installation
    VENV_PATH="$PROJECT_ROOT/.venv"
    PYTHON_BIN="$VENV_PATH/bin/python"
elif [ -d "$HOME/.local/pipx/venvs/neuravox" ]; then
    # Installed via pipx
    PYTHON_BIN="$HOME/.local/pipx/venvs/neuravox/bin/python"
elif [ -d "$HOME/.neuravox/venv" ]; then
    # Custom installation location
    PYTHON_BIN="$HOME/.neuravox/venv/bin/python"
else
    # Try to find neuravox in current environment
    if command -v neuravox &> /dev/null; then
        # Already in correct environment
        exec neuravox "$@"
    else
        echo "Error: Neuravox virtual environment not found."
        echo "Please install Neuravox using one of these methods:"
        echo "  1. Development: cd /path/to/neuravox && uv venv && uv pip install -e ."
        echo "  2. pipx: pipx install neuravox"
        echo "  3. Custom: python -m venv ~/.neuravox/venv && ~/.neuravox/venv/bin/pip install neuravox"
        exit 1
    fi
fi

# Execute neuravox with the correct Python
exec "$PYTHON_BIN" -m cli.main "$@"