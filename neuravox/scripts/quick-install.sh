#!/usr/bin/env bash
# Quick installation script for Neuravox using pipx

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}Neuravox Quick Installer${NC}"
echo "========================="

# Check for pipx
if ! command -v pipx &> /dev/null; then
    echo -e "${YELLOW}pipx not found. Would you like to install it?${NC}"
    read -p "Install pipx? [Y/n] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        echo -e "${CYAN}Installing pipx...${NC}"
        
        if command -v brew &> /dev/null; then
            brew install pipx
        elif command -v apt &> /dev/null; then
            sudo apt update && sudo apt install pipx
        elif command -v dnf &> /dev/null; then
            sudo dnf install pipx
        else
            # Fallback to pip
            python3 -m pip install --user pipx
        fi
        
        python3 -m pipx ensurepath
        
        echo -e "${GREEN}✓ pipx installed${NC}"
        echo -e "${YELLOW}Please restart your terminal or run: source ~/.bashrc${NC}"
        exit 0
    else
        echo -e "${RED}pipx is required for this installer${NC}"
        echo "Visit https://pypa.github.io/pipx/ for installation instructions"
        exit 1
    fi
fi

# Install Neuravox
echo -e "${CYAN}Installing Neuravox...${NC}"

if [ -f "pyproject.toml" ]; then
    # Installing from source directory
    pipx install .
else
    # Installing from PyPI (when published)
    echo -e "${RED}Error: Not in Neuravox directory${NC}"
    echo "Please run this script from the Neuravox project directory"
    exit 1
fi

# Initialize workspace
echo -e "${CYAN}Initializing workspace...${NC}"
neuravox init

echo -e "\n${GREEN}✅ Neuravox installed successfully!${NC}"
echo -e "\nQuick start:"
echo -e "  ${BOLD}neuravox config${NC}     # Set up API keys"
echo -e "  ${BOLD}neuravox process${NC}    # Process audio files"
echo -e "  ${BOLD}neuravox --help${NC}     # Show all commands"