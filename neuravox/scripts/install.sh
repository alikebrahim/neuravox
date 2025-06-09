#!/usr/bin/env bash
# Neuravox Installation Script
# Simple installer for ~/.neuravox with gum UI

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Installation paths
INSTALL_DIR="$HOME/.neuravox"
BIN_DIR="$HOME/.local/bin"
MAN_DIR="$HOME/.local/share/man/man1"
CONFIG_DIR="$HOME/.config/neuravox"
WORKSPACE_LINK="$HOME/neuravox.workspace"

# Check prerequisites
check_prerequisites() {
    local missing=()
    
    # Check Python 3.12+
    if command -v python3.12 &> /dev/null; then
        PYTHON_CMD="python3.12"
    elif command -v python3 &> /dev/null; then
        if python3 -c "import sys; exit(0 if sys.version_info >= (3,12) else 1)" 2>/dev/null; then
            PYTHON_CMD="python3"
        else
            missing+=("Python 3.12+ (current: $(python3 --version))")
        fi
    else
        missing+=("Python 3.12+")
    fi
    
    # Check uv
    if ! command -v uv &> /dev/null; then
        missing+=("uv (install from: https://astral.sh/uv)")
    fi
    
    # Check gum
    if ! command -v gum &> /dev/null; then
        missing+=("gum (install: go install github.com/charmbracelet/gum@latest)")
    fi
    
    if [ ${#missing[@]} -ne 0 ]; then
        echo -e "${RED}Missing prerequisites:${NC}"
        for item in "${missing[@]}"; do
            echo -e "  ${RED}✗${NC} $item"
        done
        exit 1
    fi
}

# Install Neuravox
install_neuravox() {
    echo -e "${CYAN}${BOLD}Installing Neuravox${NC}"
    echo
    
    # Check if we're in the right location
    if [ ! -d "$INSTALL_DIR" ] || [ "$PWD" != "$INSTALL_DIR" ]; then
        echo -e "${RED}Error: This script must be run from ~/.neuravox${NC}"
        echo -e "Please clone the repository to ~/.neuravox and run again:"
        echo -e "  ${BOLD}git clone <repo> ~/.neuravox${NC}"
        echo -e "  ${BOLD}cd ~/.neuravox${NC}"
        echo -e "  ${BOLD}./scripts/install.sh${NC}"
        exit 1
    fi
    
    # Create virtual environment and install dependencies
    gum spin --spinner dot --title "Creating virtual environment and installing dependencies..." -- \
        uv sync
    echo -e "${GREEN}✓${NC} Dependencies installed"
    
    # Create bin directory
    mkdir -p "$BIN_DIR"
    
    # Create launcher script
    cat > "$BIN_DIR/neuravox" << 'EOF'
#!/usr/bin/env bash
exec "$HOME/.neuravox/.venv/bin/python" -m neuravox "$@"
EOF
    chmod +x "$BIN_DIR/neuravox"
    echo -e "${GREEN}✓${NC} Launcher created at $BIN_DIR/neuravox"
    
    # Initialize workspace
    gum spin --spinner dot --title "Initializing workspace..." -- \
        "$INSTALL_DIR/.venv/bin/python" -m neuravox init
    echo -e "${GREEN}✓${NC} Workspace initialized"
    
    # Create selective symlinks
    if [ -e "$WORKSPACE_LINK" ]; then
        echo -e "${YELLOW}!${NC} ~/neuravox.workspace already exists, skipping symlink creation"
    else
        mkdir -p "$WORKSPACE_LINK"
        ln -sf "$INSTALL_DIR/workspace/input" "$WORKSPACE_LINK/input"
        ln -sf "$INSTALL_DIR/workspace/processed" "$WORKSPACE_LINK/processed"
        ln -sf "$INSTALL_DIR/workspace/transcribed" "$WORKSPACE_LINK/transcribed"
        echo -e "${GREEN}✓${NC} Created workspace symlinks at ~/neuravox.workspace"
    fi
    
    # Install man pages
    mkdir -p "$MAN_DIR"
    for page in neuravox.1 neuravox-init.1 neuravox-process.1 neuravox-status.1 neuravox-config.1; do
        if [ -f "$INSTALL_DIR/docs/man/$page" ]; then
            cp "$INSTALL_DIR/docs/man/$page" "$MAN_DIR/"
        fi
    done
    mandb -u >/dev/null 2>&1 || true
    echo -e "${GREEN}✓${NC} Man pages installed"
    
    # Check PATH
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        echo
        echo -e "${YELLOW}Important:${NC} Add ~/.local/bin to your PATH"
        echo -e "Add this line to your shell configuration file:"
        echo -e '  export PATH="$HOME/.local/bin:$PATH"'
        echo -e "Then reload your shell or run: source ~/.bashrc"
    fi
    
    echo
    echo -e "${GREEN}${BOLD}Installation complete!${NC}"
    echo
    echo -e "Quick start:"
    echo -e "  ${BOLD}neuravox --help${NC}      # Show help"
    echo -e "  ${BOLD}neuravox config${NC}      # Configure API keys"
    echo -e "  ${BOLD}neuravox process${NC}     # Process audio files"
    echo
    echo -e "Workspace: ${BOLD}~/neuravox.workspace${NC}"
    echo -e "Man pages: ${BOLD}man neuravox${NC}"
}

# Uninstall Neuravox
uninstall_neuravox() {
    echo -e "${CYAN}${BOLD}Uninstalling Neuravox${NC}"
    echo
    
    if gum confirm "This will remove Neuravox completely. Continue?"; then
        # Remove launcher
        if [ -f "$BIN_DIR/neuravox" ]; then
            rm "$BIN_DIR/neuravox"
            echo -e "${GREEN}✓${NC} Removed launcher"
        fi
        
        # Remove workspace symlinks
        if [ -L "$WORKSPACE_LINK/input" ] || [ -L "$WORKSPACE_LINK/processed" ] || [ -L "$WORKSPACE_LINK/transcribed" ]; then
            rm -f "$WORKSPACE_LINK/input" "$WORKSPACE_LINK/processed" "$WORKSPACE_LINK/transcribed"
            rmdir "$WORKSPACE_LINK" 2>/dev/null || true
            echo -e "${GREEN}✓${NC} Removed workspace symlinks"
        fi
        
        # Remove man pages
        for page in neuravox.1 neuravox-init.1 neuravox-process.1 neuravox-status.1 neuravox-config.1; do
            rm -f "$MAN_DIR/$page"
        done
        mandb -u >/dev/null 2>&1 || true
        echo -e "${GREEN}✓${NC} Removed man pages"
        
        # Remove config directory
        if [ -d "$CONFIG_DIR" ] && gum confirm "Remove configuration directory (~/.config/neuravox)?"; then
            rm -rf "$CONFIG_DIR"
            echo -e "${GREEN}✓${NC} Removed configuration"
        fi
        
        # Remove installation directory
        if [ -d "$INSTALL_DIR" ] && gum confirm "Remove installation directory (~/.neuravox)?"; then
            rm -rf "$INSTALL_DIR"
            echo -e "${GREEN}✓${NC} Removed installation directory"
        fi
        
        echo
        echo -e "${GREEN}Neuravox has been uninstalled${NC}"
    else
        echo -e "${YELLOW}Uninstall cancelled${NC}"
    fi
}

# Main
main() {
    # Banner
    echo -e "${CYAN}${BOLD}"
    echo "╔════════════════════════════════════════╗"
    echo "║         Neuravox Installer             ║"
    echo "║    Neural Audio Processing Platform    ║"
    echo "╚════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # Check prerequisites
    check_prerequisites
    
    # Main menu
    CHOICE=$(gum choose --header "What would you like to do?" \
        "Install Neuravox" \
        "Uninstall Neuravox" \
        "Exit")
    
    case "$CHOICE" in
        "Install Neuravox")
            install_neuravox
            ;;
        "Uninstall Neuravox")
            uninstall_neuravox
            ;;
        *)
            echo -e "${YELLOW}Exiting${NC}"
            ;;
    esac
}

main "$@"