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
    BOOK="📚"
else
    ROCKET="[>]"
    CHECK="[✓]"
    WRENCH="[*]"
    PACKAGE="[#]"
    BRAIN="[@]"
    BOOK="[M]"
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
    # First check the parent shell (what the user is actually using)
    # This is more accurate than checking the current shell's version variables
    local parent_shell=""
    
    # Try to get the parent shell from environment or ps
    if [ -n "$SHELL" ]; then
        parent_shell="$SHELL"
    elif command -v ps &> /dev/null; then
        # Try to get parent process shell
        parent_shell=$(ps -p $PPID -o comm= 2>/dev/null || echo "")
    fi
    
    # Determine shell based on parent shell path/name
    case "$parent_shell" in
        */zsh|zsh) 
            SHELL_RC="$HOME/.zshrc"
            SHELL_NAME="zsh"
            ;;
        */bash|bash) 
            SHELL_RC="$HOME/.bashrc"
            SHELL_NAME="bash"
            ;;
        */fish|fish)
            SHELL_RC="$HOME/.config/fish/config.fish"
            SHELL_NAME="fish"
            ;;
        *)
            # If we can't detect parent, fall back to version variables
            if [ -n "$ZSH_VERSION" ]; then
                SHELL_RC="$HOME/.zshrc"
                SHELL_NAME="zsh"
            elif [ -n "$BASH_VERSION" ]; then
                SHELL_RC="$HOME/.bashrc"
                SHELL_NAME="bash"
            else
                SHELL_RC="$HOME/.profile"
                SHELL_NAME="sh"
            fi
            ;;
    esac
    
    echo -e "${GREEN}${CHECK}${NC} Detected shell: ${BOLD}$SHELL_NAME${NC}"
}

# Check for required package manager
check_uv() {
    if command -v uv &> /dev/null; then
        echo -e "${GREEN}${CHECK}${NC} Found ${BOLD}uv${NC} (required package manager)"
    else
        echo -e "${RED}Error: uv is required but not found${NC}"
        echo -e "\nTo install uv, run:"
        echo -e "  ${BOLD}curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
        echo -e "\nThen restart your terminal or run:"
        echo -e "  ${BOLD}source ~/.local/bin/env${NC}"
        exit 1
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
            # Create temp file for capturing errors
            local error_file=$(mktemp)
            if ! gum spin --spinner dot --title "$title" -- bash -c "$cmd 2>'$error_file'"; then
                echo -e "${RED}✗ Failed: $title${NC}"
                if [ -s "$error_file" ]; then
                    echo -e "${RED}Error details:${NC}"
                    cat "$error_file"
                fi
                rm -f "$error_file"
                exit 1
            fi
            rm -f "$error_file"
            ;;
        *)
            echo -e "${CYAN}${WRENCH}${NC} $title..."
            if ! eval "$cmd"; then
                echo -e "${RED}✗ Failed: $title${NC}"
                exit 1
            fi
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
check_uv
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
echo -e "  Package manager:  ${BOLD}uv${NC} (required)"

if ! confirm "Proceed with installation?"; then
    echo -e "${YELLOW}Installation cancelled${NC}"
    exit 0
fi

# Create directories
echo -e "\n${CYAN}${ROCKET} Starting Installation${NC}"

# Debug: Show installation mode
if [ "$IS_DEV" = true ]; then
    echo -e "${YELLOW}Running in development mode${NC}"
else
    echo -e "${GREEN}Running in user installation mode${NC}"
fi

if [ "$IS_DEV" != true ]; then
    # Check if installation directory already exists with files
    if [ -d "$INSTALL_DIR" ] && [ -f "$INSTALL_DIR/pyproject.toml" ]; then
        echo -e "${YELLOW}! Installation directory already exists at $INSTALL_DIR${NC}"
        if ! confirm "Remove existing installation and continue?"; then
            echo -e "${YELLOW}Installation cancelled${NC}"
            exit 0
        fi
        echo -e "${CYAN}${WRENCH} Removing existing installation...${NC}"
        rm -rf "$INSTALL_DIR"
    fi
    
    # Create installation directory
    show_progress "Creating installation directory" "mkdir -p '$INSTALL_DIR'"
    
    # Copy project files
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
    
    # Export vars for subshell
    export INSTALL_DIR PROJECT_ROOT
    
    # Copy project files with direct commands
    show_progress "Copying project files" "
        echo 'DEBUG: PROJECT_ROOT=$PROJECT_ROOT' && \
        echo 'DEBUG: INSTALL_DIR=$INSTALL_DIR' && \
        echo 'DEBUG: Checking if source directories exist...' && \
        
        # Check if source directories exist
        for dir in modules core cli config scripts docs/man; do
            if [ ! -e \"\$PROJECT_ROOT/\$dir\" ]; then
                echo \"ERROR: Source directory not found: \$PROJECT_ROOT/\$dir\"
                exit 1
            fi
        done && \
        
        # Create essential directories first
        mkdir -p \"\$INSTALL_DIR\"/{modules,core,cli,config,scripts,docs/man} || {
            echo 'ERROR: Failed to create directories in $INSTALL_DIR'
            exit 1
        } && \
        
        # Copy essential directories
        cp -r \"\$PROJECT_ROOT\"/modules \"\$INSTALL_DIR/\" && \
        cp -r \"\$PROJECT_ROOT\"/core \"\$INSTALL_DIR/\" && \
        cp -r \"\$PROJECT_ROOT\"/cli \"\$INSTALL_DIR/\" && \
        cp -r \"\$PROJECT_ROOT\"/config \"\$INSTALL_DIR/\" && \
        cp -r \"\$PROJECT_ROOT\"/scripts \"\$INSTALL_DIR/\" && \
        cp -r \"\$PROJECT_ROOT\"/docs/man \"\$INSTALL_DIR\"/docs/ && \
        
        # Copy essential files
        cp \"\$PROJECT_ROOT\"/pyproject.toml \"\$INSTALL_DIR/\" && \
        { cp \"\$PROJECT_ROOT\"/README.md \"\$INSTALL_DIR/\" 2>/dev/null || true; } && \
        { cp \"\$PROJECT_ROOT\"/CLAUDE.md \"\$INSTALL_DIR/\" 2>/dev/null || true; } && \
        
        # Clean up any __pycache__ that might have been copied
        { find \"\$INSTALL_DIR\" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true; } && \
        { find \"\$INSTALL_DIR\" -name '*.pyc' -delete 2>/dev/null || true; }
    "
fi

# Create user bin directory if needed
mkdir -p "$BIN_DIR"

# Create virtual environment and install dependencies with uv
show_progress "Creating virtual environment and installing dependencies" "cd '$INSTALL_DIR' && uv sync"

# Create wrapper script
echo -e "\n${CYAN}${WRENCH} Creating launcher...${NC}"

# uv always creates .venv directory
PYTHON_BIN="$INSTALL_DIR/.venv/bin/python"

cat > "$BIN_DIR/neuravox" << EOF
#!/usr/bin/env bash
# Neuravox launcher - auto-manages virtual environment

# Always use the installed virtual environment
exec "$PYTHON_BIN" -m cli.main "\$@"
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
INIT_PYTHON="$INSTALL_DIR/.venv/bin/python"

# Create workspace at ~/.neuravox/workspace
WORKSPACE_DIR="$HOME/.neuravox/workspace"
show_progress "Creating workspace structure" "cd '$INSTALL_DIR' && $INIT_PYTHON -m cli.main init --workspace '$WORKSPACE_DIR'"

# Create symlink from ~/neuravox.workspace to ~/.neuravox/workspace
echo -e "\n${CYAN}${WRENCH} Creating workspace symlink...${NC}"
ln -sf "$WORKSPACE_DIR" "$HOME/neuravox.workspace"
echo -e "${GREEN}${CHECK}${NC} Created symlink: ${BOLD}~/neuravox.workspace${NC} → ${BOLD}~/.neuravox/workspace${NC}"

# Install man pages
echo -e "\n${CYAN}${PACKAGE} Installing man pages...${NC}"
MAN_DIR="$HOME/.local/share/man/man1"
mkdir -p "$MAN_DIR"

MAN_PAGES=(
    "neuravox.1"
    "neuravox-init.1"
    "neuravox-process.1"
    "neuravox-status.1"
    "neuravox-config.1"
)

for page in "${MAN_PAGES[@]}"; do
    if [ -f "$INSTALL_DIR/docs/man/$page" ]; then
        cp "$INSTALL_DIR/docs/man/$page" "$MAN_DIR/"
        echo -e "  ${CHECK} Installed $page"
    fi
done

# Update man database
show_progress "Updating man database" "mandb -u >/dev/null 2>&1 || true"

# Check if MANPATH needs to be added
if [[ ":$MANPATH:" != *":$HOME/.local/share/man:"* ]] && [ -n "$SELECTED_RC" ] && [ -f "$SELECTED_RC" ]; then
    # Add MANPATH update
    echo "" >> "$SELECTED_RC"
    echo "# Added by Neuravox installer - man pages" >> "$SELECTED_RC"
    echo "export MANPATH=\"\$HOME/.local/share/man:\$MANPATH\"" >> "$SELECTED_RC"
    MANPATH_UPDATED=true
fi

# Success message
echo -e "\n${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${CHECK} Neuravox installed successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"

echo -e "\n${CYAN}Installation Details:${NC}"
echo -e "  ${PACKAGE} Installed to: ${BOLD}$INSTALL_DIR${NC}"
echo -e "  ${ROCKET} Command available at: ${BOLD}$BIN_DIR/neuravox${NC}"
echo -e "  ${BRAIN} Workspace created at: ${BOLD}~/neuravox.workspace${NC}"
echo -e "  ${BOOK} Man pages installed: ${BOLD}man neuravox${NC}"

if [ "$PATH_UPDATED" = true ] || [ "$MANPATH_UPDATED" = true ]; then
    echo -e "\n${YELLOW}${WRENCH} Action Required:${NC}"
    echo -e "  Run: ${BOLD}source $SELECTED_RC${NC}"
    echo -e "  Or start a new terminal session"
fi

echo -e "\n${CYAN}Quick Start:${NC}"
echo -e "  ${BOLD}neuravox --help${NC}              # Show help"
echo -e "  ${BOLD}neuravox config${NC}              # Configure API keys"
echo -e "  ${BOLD}neuravox process --interactive${NC} # Process audio files"

echo -e "\n${MAGENTA}${BRAIN} Ready to process some audio!${NC}"