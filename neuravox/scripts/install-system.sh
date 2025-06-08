#!/usr/bin/env bash
# System-wide installation script for Neuravox

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Neuravox System Installation${NC}"
echo "================================="

# Check if running as root for system-wide install
if [ "$1" == "--system" ] && [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: System-wide installation requires root privileges${NC}"
    echo "Run: sudo $0 --system"
    exit 1
fi

# Detect installation type
if [ "$1" == "--system" ]; then
    INSTALL_DIR="/opt/neuravox"
    BIN_DIR="/usr/local/bin"
    echo "Installing system-wide to $INSTALL_DIR"
else
    INSTALL_DIR="$HOME/.neuravox"
    BIN_DIR="$HOME/.local/bin"
    echo "Installing for current user to $INSTALL_DIR"
    
    # Create user bin directory if it doesn't exist
    mkdir -p "$BIN_DIR"
    
    # Add to PATH if not already there
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        echo -e "${YELLOW}Note: Adding $BIN_DIR to PATH${NC}"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
        echo "Please run: source ~/.bashrc"
    fi
fi

# Create installation directory
echo "Creating installation directory..."
mkdir -p "$INSTALL_DIR"

# Copy project files
echo "Copying project files..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Use rsync if available, otherwise cp
if command -v rsync &> /dev/null; then
    rsync -av --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
          --exclude='.git' --exclude='*.egg-info' \
          "$PROJECT_ROOT/" "$INSTALL_DIR/"
else
    cp -r "$PROJECT_ROOT"/* "$INSTALL_DIR/"
    # Clean up unwanted files
    find "$INSTALL_DIR" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
    find "$INSTALL_DIR" -name '*.pyc' -delete 2>/dev/null || true
fi

# Create virtual environment
echo "Creating virtual environment..."
cd "$INSTALL_DIR"
python3.12 -m venv venv

# Install dependencies
echo "Installing dependencies..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -e .

# Create wrapper script
echo "Creating launcher..."
cat > "$BIN_DIR/neuravox" << 'EOF'
#!/usr/bin/env bash
# Neuravox launcher - auto-manages virtual environment

INSTALL_DIR="__INSTALL_DIR__"
exec "$INSTALL_DIR/venv/bin/python" -m cli.main "$@"
EOF

# Replace placeholder with actual install directory
sed -i "s|__INSTALL_DIR__|$INSTALL_DIR|g" "$BIN_DIR/neuravox"
chmod +x "$BIN_DIR/neuravox"

# Initialize workspace
echo "Initializing workspace..."
"$BIN_DIR/neuravox" init

echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "Neuravox has been installed to: $INSTALL_DIR"
echo "Command available at: $BIN_DIR/neuravox"
echo ""
echo "To get started:"
echo "  neuravox --help"
echo "  neuravox process --interactive"
echo ""

if [ "$1" != "--system" ]; then
    echo -e "${YELLOW}Note: If 'neuravox' command is not found, run:${NC}"
    echo "  source ~/.bashrc"
fi