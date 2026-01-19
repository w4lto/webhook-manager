#!/bin/bash

set -e

echo "╔════════════════════════════════════════╗"
echo "║   🚇 Webhook Tunnel Installer          ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.8+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✅ Python found: ${PYTHON_VERSION}${NC}"

REQUIRED_VERSION="3.8"
CURRENT_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$CURRENT_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}❌ Python ${REQUIRED_VERSION}+ required, but ${CURRENT_VERSION} found${NC}"
    exit 1
fi

echo -e "${CYAN}Checking pip installation...${NC}"
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}❌ pip3 not found. Installing pip...${NC}"
    python3 -m ensurepip --upgrade
fi
echo -e "${GREEN}✅ pip found${NC}"

echo -e "${CYAN}Checking socat installation...${NC}"
if ! command -v socat &> /dev/null; then
    echo -e "${YELLOW}⚠️  socat not found. Attempting to install...${NC}"
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &> /dev/null; then
            echo "Installing via apt-get..."
            sudo apt-get update -qq
            sudo apt-get install -y socat
        elif command -v dnf &> /dev/null; then
            echo "Installing via dnf..."
            sudo dnf install -y socat
        elif command -v yum &> /dev/null; then
            echo "Installing via yum..."
            sudo yum install -y socat
        elif command -v pacman &> /dev/null; then
            echo "Installing via pacman..."
            sudo pacman -S --noconfirm socat
        else
            echo -e "${RED}❌ Could not install socat automatically${NC}"
            echo "Please install manually: sudo apt-get install socat"
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            echo "Installing via Homebrew..."
            brew install socat
        else
            echo -e "${RED}❌ Homebrew not found${NC}"
            echo "Install Homebrew first:"
            echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
            exit 1
        fi
    else
        echo -e "${RED}❌ Unsupported OS: $OSTYPE${NC}"
        exit 1
    fi
fi

if command -v socat &> /dev/null; then
    echo -e "${GREEN}✅ socat found: $(socat -V 2>&1 | head -n1)${NC}"
else
    echo -e "${RED}❌ socat installation failed${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}Installing webhook-tunnel...${NC}"

if [ -f "setup.py" ]; then
    echo "Installing from local source..."
    pip3 install -e .
else
    echo "Installing from PyPI..."
    pip3 install webhook-tunnel
fi

echo ""
echo -e "${CYAN}Verifying installation...${NC}"

COMMANDS=("tunnel" "tunnel-tui" "tunnel-server")
ALL_FOUND=true

for cmd in "${COMMANDS[@]}"; do
    if command -v "$cmd" &> /dev/null; then
        echo -e "${GREEN}✅ $cmd${NC}"
    else
        echo -e "${YELLOW}⚠️  $cmd not found in PATH${NC}"
        ALL_FOUND=false
    fi
done

echo ""
if [ "$ALL_FOUND" = true ]; then
    echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ✅ Installation completed!           ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}Available commands:${NC}"
    echo "  • tunnel         - CLI interface"
    echo "  • tunnel-tui     - Interactive TUI"
    echo "  • tunnel-server  - Example webhook server"
    echo ""
    echo -e "${CYAN}Quick start:${NC}"
    echo "  1. Start your local service (e.g., npm start on port 3000)"
    echo "  2. Run: tunnel start myapi 3000"
    echo "  3. Or use TUI: tunnel-tui"
    echo ""
    echo -e "${CYAN}Documentation:${NC}"
    echo "  • tunnel --help"
    echo "  • https://github.com/yourusername/webhook-tunnel"
else
    echo -e "${YELLOW}╔════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║   ⚠️  Installation partially complete  ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo "Commands not found in PATH. You may need to add to your PATH:"
    echo ""
    echo "Add to ~/.bashrc or ~/.zshrc:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "Then run:"
    echo "  source ~/.bashrc  # or source ~/.zshrc"
fi
