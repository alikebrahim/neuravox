#!/usr/bin/env bash
# System-wide installation script for Neuravox
# Features: Shell detection, uv preference, modern TUI with fallbacks

set -e

# Colors for output (works even without gum)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Emoji support detection
if echo -e "\U1F680" | grep -q "🚀"; then
    ROCKET="🚀"
    CHECK="✅"
    WRENCH="🔧"
    PACKAGE="📦"
    BRAIN="🧠"
else
    ROCKET="[>]"
    CHECK="[✓]"
    WRENCH="[*]"
    PACKAGE="[#]"
    BRAIN="[@]"
fi

# Banner
echo -e "${CYAN}${BOLD}"
echo "╔════════════════════════════════════════╗"
echo "║        ${BRAIN} Neuravox Installer ${BRAIN}        ║"
echo "║    Neural Audio Processing Platform    ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

# Detect shell and RC file
detect_shell() {
    if [ -n "$ZSH_VERSION" ]; then
        SHELL_RC="$HOME/.zshrc"
        SHELL_NAME="zsh"
    elif [ -n "$BASH_VERSION" ]; then
        SHELL_RC="$HOME/.bashrc"
        SHELL_NAME="bash"
    else
        # Fallback to checking $SHELL
        case "$SHELL" in
            */zsh) 
                SHELL_RC="$HOME/.zshrc"
                SHELL_NAME="zsh"
                ;;
            */bash) 
                SHELL_RC="$HOME/.bashrc"
                SHELL_NAME="bash"
                ;;
            */fish)
                SHELL_RC="$HOME/.config/fish/config.fish"
                SHELL_NAME="fish"
                ;;
            *)
                SHELL_RC="$HOME/.profile"
                SHELL_NAME="sh"
                ;;
        esac
    fi
    echo -e "${GREEN}${CHECK}${NC} Detected shell: ${BOLD}$SHELL_NAME${NC}"
}

# Detect package manager
detect_package_manager() {
    if command -v uv &> /dev/null; then
        VENV_CMD="uv venv"
        PIP_CMD="uv pip"
        PIP_INSTALL="uv pip install"
        PIP_SYNC="uv pip sync"
        PACKAGE_MANAGER="uv"
        echo -e "${GREEN}${CHECK}${NC} Found ${BOLD}uv${NC} (fast package manager)"
    else
        echo -e "${YELLOW}!${NC} uv not found, using standard pip"
        echo -e "  ${CYAN}Tip: Install uv for 10x faster installs: ${BOLD}curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
        VENV_CMD="python3.12 -m venv"
        PIP_CMD="pip"
        PACKAGE_MANAGER="pip"
        
        # Will be set after venv creation
        PIP_INSTALL=""
        PIP_SYNC=""
    fi
}

# Detect menu system
detect_menu_system() {
    if command -v gum &> /dev/null; then
        MENU_SYSTEM="gum"
        echo -e "${GREEN}${CHECK}${NC} Found ${BOLD}gum${NC} for beautiful menus"
    elif command -v whiptail &> /dev/null; then
        MENU_SYSTEM="whiptail"
        echo -e "${GREEN}${CHECK}${NC} Found ${BOLD}whiptail${NC} for menus"
    elif command -v dialog &> /dev/null; then
        MENU_SYSTEM="dialog"
        echo -e "${GREEN}${CHECK}${NC} Found ${BOLD}dialog${NC} for menus"
    else
        MENU_SYSTEM="select"
        echo -e "${YELLOW}!${NC} No TUI found, using basic menus"
        echo -e "  ${CYAN}Tip: Install gum for better UX: ${BOLD}go install github.com/charmbracelet/gum@latest${NC}"
    fi
}

# Unified menu function
menu_choose() {
    local prompt="$1"
    shift
    local options=("$@")
    local result=""
    
    case "$MENU_SYSTEM" in
        gum)
            result=$(gum choose --header "$prompt" --cursor.foreground="212" "${options[@]}")
            ;;
        whiptail)
            local args=()
            for i in "${!options[@]}"; do
                args+=("$((i+1))" "${options[$i]}")
            done
            local choice=$(whiptail --title "Neuravox Installer" --menu "$prompt" 20 70 10 "${args[@]}" 3>&1 1>&2 2>&3)
            if [ -n "$choice" ]; then
                result="${options[$((choice-1))]}"
            fi
            ;;
        dialog)
            local args=()
            for i in "${!options[@]}"; do
                args+=("$((i+1))" "${options[$i]}")
            done
            local choice=$(dialog --menu "$prompt" 20 70 10 "${args[@]}" 3>&1 1>&2 2>&3)
            if [ -n "$choice" ]; then
                result="${options[$((choice-1))]}"
            fi
            ;;
        *)
            # Fallback to select
            echo -e "\n${CYAN}${prompt}${NC}"
            PS3="Enter choice (1-${#options[@]}): "
            select opt in "${options[@]}"; do
                if [ -n "$opt" ]; then
                    result="$opt"
                    break
                fi
            done
            ;;
    esac
    
    echo "$result"
}

# Confirm function
confirm() {
    local prompt="$1"
    local default="${2:-no}"
    
    case "$MENU_SYSTEM" in
        gum)
            if gum confirm "$prompt"; then
                return 0
            else
                return 1
            fi
            ;;
        whiptail)
            if whiptail --yesno "$prompt" 10 60; then
                return 0
            else
                return 1
            fi
            ;;
        *)
            # Simple y/n prompt
            local yn
            if [ "$default" = "yes" ]; then
                read -p "$prompt [Y/n] " yn
                yn=${yn:-y}
            else
                read -p "$prompt [y/N] " yn
                yn=${yn:-n}
            fi
            case $yn in
                [Yy]* ) return 0;;
                * ) return 1;;
            esac
            ;;
    esac
}

# Progress indicator
show_progress() {
    local title="$1"
    local cmd="$2"
    
    case "$MENU_SYSTEM" in
        gum)
            gum spin --spinner dot --title "$title" -- bash -c "$cmd"
            ;;
        *)
            echo -e "${CYAN}${WRENCH}${NC} $title..."
            eval "$cmd"
            ;;
    esac
}

# Check Python version
check_python() {
    echo -e "\n${CYAN}Checking Python version...${NC}"
    
    # Try python3.12 first
    if command -v python3.12 &> /dev/null; then
        PYTHON_CMD="python3.12"
    elif command -v python3 &> /dev/null; then
        # Check if python3 is 3.12+
        if python3 -c "import sys; exit(0 if sys.version_info >= (3,12) else 1)" 2>/dev/null; then
            PYTHON_CMD="python3"
        else
            echo -e "${RED}Error: Python 3.12+ required but not found${NC}"
            echo -e "Current version: $(python3 --version)"
            exit 1
        fi
    else
        echo -e "${RED}Error: Python 3 not found${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}${CHECK}${NC} Found Python: $($PYTHON_CMD --version)"
}

# Main installation starts here
echo ""
detect_shell
detect_package_manager
detect_menu_system
check_python

# Choose installation type
echo -e "\n${CYAN}${PACKAGE} Installation Options${NC}"
INSTALL_TYPE=$(menu_choose "Select installation type:" \
    "User Install (~/.neuravox) - Recommended" \
    "System Install (/opt/neuravox) - Requires sudo" \
    "Development Mode (current directory)" \
    "Cancel Installation")

if [ "$INSTALL_TYPE" = "Cancel Installation" ] || [ -z "$INSTALL_TYPE" ]; then
    echo -e "${YELLOW}Installation cancelled${NC}"
    exit 0
fi

# Set installation paths based on choice
case "$INSTALL_TYPE" in
    "User Install"*)
        INSTALL_DIR="$HOME/.neuravox"
        BIN_DIR="$HOME/.local/bin"
        NEEDS_SUDO=false
        ;;
    "System Install"*)
        INSTALL_DIR="/opt/neuravox"
        BIN_DIR="/usr/local/bin"
        NEEDS_SUDO=true
        ;;
    "Development Mode"*)
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        INSTALL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
        BIN_DIR="$HOME/.local/bin"
        NEEDS_SUDO=false
        IS_DEV=true
        ;;
esac

# Check sudo if needed
if [ "$NEEDS_SUDO" = true ] && [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: System installation requires root privileges${NC}"
    echo "Please run: sudo $0"
    exit 1
fi

# Choose shell configuration
echo -e "\n${CYAN}${WRENCH} Shell Configuration${NC}"
SHELL_OPTIONS=(
    "$SHELL_RC (detected $SHELL_NAME)"
    "$HOME/.zshrc"
    "$HOME/.bashrc"
    "$HOME/.profile"
    "Skip shell configuration"
)

SELECTED_RC=$(menu_choose "Configure shell startup file:" "${SHELL_OPTIONS[@]}")

# Extract just the path from the selection
case "$SELECTED_RC" in
    *"Skip"*) SELECTED_RC="";;
    *) SELECTED_RC=$(echo "$SELECTED_RC" | cut -d' ' -f1);;
esac

# Confirm installation
echo -e "\n${CYAN}${ROCKET} Installation Summary${NC}"
echo -e "  Install location: ${BOLD}$INSTALL_DIR${NC}"
echo -e "  Binary location:  ${BOLD}$BIN_DIR${NC}"
echo -e "  Shell config:     ${BOLD}${SELECTED_RC:-None}${NC}"
echo -e "  Package manager:  ${BOLD}$PACKAGE_MANAGER${NC}"

if ! confirm "Proceed with installation?"; then
    echo -e "${YELLOW}Installation cancelled${NC}"
    exit 0
fi

# Create directories
echo -e "\n${CYAN}${ROCKET} Starting Installation${NC}"

if [ "$IS_DEV" != true ]; then
    # Create installation directory
    show_progress "Creating installation directory" "mkdir -p '$INSTALL_DIR'"
    
    # Copy project files
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
    
    show_progress "Copying project files" "
        if command -v rsync &> /dev/null; then
            rsync -a --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
                  --exclude='.git' --exclude='*.egg-info' --exclude='.pytest_cache' \
                  --exclude='tests' --exclude='docs' \
                  '$PROJECT_ROOT/' '$INSTALL_DIR/'
        else
            cp -r '$PROJECT_ROOT'/* '$INSTALL_DIR/'
            find '$INSTALL_DIR' -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
            find '$INSTALL_DIR' -name '*.pyc' -delete 2>/dev/null || true
        fi
    "
fi

# Create user bin directory if needed
mkdir -p "$BIN_DIR"

# Change to installation directory
cd "$INSTALL_DIR"

# Create virtual environment
if [ "$PACKAGE_MANAGER" = "uv" ]; then
    show_progress "Creating virtual environment with uv" "$VENV_CMD"
else
    show_progress "Creating virtual environment" "$PYTHON_CMD -m venv venv"
    # Set pip commands for standard pip
    PIP_INSTALL="./venv/bin/pip install"
    PIP_CMD="./venv/bin/pip"
fi

# Install dependencies
if [ "$PACKAGE_MANAGER" = "uv" ]; then
    if [ "$IS_DEV" = true ]; then
        show_progress "Installing in development mode" "$PIP_INSTALL -e ."
    else
        show_progress "Installing dependencies" "$PIP_INSTALL ."
    fi
else
    show_progress "Upgrading pip" "$PIP_CMD install --upgrade pip"
    if [ "$IS_DEV" = true ]; then
        show_progress "Installing in development mode" "$PIP_INSTALL -e ."
    else
        show_progress "Installing dependencies" "$PIP_INSTALL ."
    fi
fi

# Create wrapper script
echo -e "\n${CYAN}${WRENCH} Creating launcher...${NC}"

if [ "$PACKAGE_MANAGER" = "uv" ]; then
    PYTHON_BIN="$INSTALL_DIR/.venv/bin/python"
else
    PYTHON_BIN="$INSTALL_DIR/venv/bin/python"
fi

cat > "$BIN_DIR/neuravox" << EOF
#!/usr/bin/env bash
# Neuravox launcher - auto-manages virtual environment

if [ "$IS_DEV" = true ]; then
    # Development mode - check if we're in the right venv
    if [ -z "\$VIRTUAL_ENV" ] || [ "\$VIRTUAL_ENV" != "$INSTALL_DIR/.venv" ]; then
        echo "Please activate the development virtual environment:"
        echo "  cd $INSTALL_DIR"
        echo "  source .venv/bin/activate"
        exit 1
    fi
    exec python -m cli.main "\$@"
else
    # Production mode - use embedded venv
    exec "$PYTHON_BIN" -m cli.main "\$@"
fi
EOF

chmod +x "$BIN_DIR/neuravox"

# Update shell configuration
if [ -n "$SELECTED_RC" ] && [ -f "$SELECTED_RC" ]; then
    echo -e "\n${CYAN}${WRENCH} Updating shell configuration...${NC}"
    
    # Check if PATH update is needed
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        # Add PATH update
        echo "" >> "$SELECTED_RC"
        echo "# Added by Neuravox installer" >> "$SELECTED_RC"
        echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$SELECTED_RC"
        PATH_UPDATED=true
    fi
fi

# Initialize workspace
echo -e "\n${CYAN}${BRAIN} Initializing Neuravox workspace...${NC}"
if [ "$PACKAGE_MANAGER" = "uv" ]; then
    INIT_PYTHON="$INSTALL_DIR/.venv/bin/python"
else
    INIT_PYTHON="$INSTALL_DIR/venv/bin/python"
fi

show_progress "Creating workspace structure" "$INIT_PYTHON -m cli.main init --non-interactive"

# Success message
echo -e "\n${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${CHECK} Neuravox installed successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"

echo -e "\n${CYAN}Installation Details:${NC}"
echo -e "  ${PACKAGE} Installed to: ${BOLD}$INSTALL_DIR${NC}"
echo -e "  ${ROCKET} Command available at: ${BOLD}$BIN_DIR/neuravox${NC}"
echo -e "  ${BRAIN} Workspace created at: ${BOLD}$HOME/neuravox${NC}"

if [ "$PATH_UPDATED" = true ]; then
    echo -e "\n${YELLOW}${WRENCH} Action Required:${NC}"
    echo -e "  Run: ${BOLD}source $SELECTED_RC${NC}"
    echo -e "  Or start a new terminal session"
fi

echo -e "\n${CYAN}Quick Start:${NC}"
echo -e "  ${BOLD}neuravox --help${NC}              # Show help"
echo -e "  ${BOLD}neuravox config${NC}              # Configure API keys"
echo -e "  ${BOLD}neuravox process --interactive${NC} # Process audio files"

echo -e "\n${MAGENTA}${BRAIN} Ready to process some audio!${NC}"