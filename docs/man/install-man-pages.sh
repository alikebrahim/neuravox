#!/bin/bash
# Install man pages for neuravox platform

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAN_PAGES=(
    "neuravox.1"
    "neuravox-init.1"
    "neuravox-process.1"
    "neuravox-status.1"
    "neuravox-config.1"
)

echo "Neuravox - Man Page Installer"
echo "==========================================="
echo

# Check if running with sudo
if [ "$EUID" -eq 0 ]; then
    # System-wide installation
    MAN_DIR="/usr/local/share/man/man1"
    echo "Installing system-wide to $MAN_DIR"
else
    # User installation
    MAN_DIR="$HOME/.local/share/man/man1"
    echo "Installing for current user to $MAN_DIR"
    echo "Note: Run with sudo for system-wide installation"
fi

echo

# Create man directory if it doesn't exist
mkdir -p "$MAN_DIR"

# Copy man pages
echo "Installing man pages..."
for page in "${MAN_PAGES[@]}"; do
    if [ -f "$SCRIPT_DIR/$page" ]; then
        cp "$SCRIPT_DIR/$page" "$MAN_DIR/"
        echo "  ✓ Installed $page"
    else
        echo "  ✗ Warning: $page not found"
    fi
done

echo

# Update man database
echo "Updating man database..."
if [ "$EUID" -eq 0 ]; then
    mandb >/dev/null 2>&1 || true
else
    mandb -u >/dev/null 2>&1 || true
    
    # Check if MANPATH is set correctly
    if [[ ":$MANPATH:" != *":$HOME/.local/share/man:"* ]]; then
        echo
        echo "⚠️  IMPORTANT: Add this to your shell profile (.bashrc, .zshrc, etc.):"
        echo
        echo "    export MANPATH=\"\$HOME/.local/share/man:\$MANPATH\""
        echo
        echo "Then reload your shell or run: source ~/.bashrc"
    fi
fi

echo
echo "✅ Installation complete!"
echo
echo "You can now use:"
echo "  man neuravox"
echo "  man neuravox-process"
echo "  man neuravox-init"
echo "  man neuravox-status"
echo "  man neuravox-config"