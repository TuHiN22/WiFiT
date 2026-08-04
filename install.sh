#!/bin/bash
#
# WiFiT Installation Script
# Author: TuHiN
# Version: 2.0.0
# Platform: Rooted Android + Termux
# GitHub: https://github.com/TuHiN22/WiFiT
#

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Banner
show_banner() {
    clear
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                 WiFiT Installer v2.0.0                      ║"
    echo "║         Professional WPS Testing Toolkit for Termux         ║"
    echo "║                      Author: TuHiN                           ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check if running in Termux
check_termux() {
    if [ -d "/data/data/com.termux" ]; then
        echo -e "${GREEN}[+] Termux environment detected${NC}"
        return 0
    else
        echo -e "${YELLOW}[!] This script is optimized for Termux${NC}"
        return 1
    fi
}

# Install dependencies for Termux
install_dependencies_termux() {
    echo -e "${YELLOW}[*] Installing Termux dependencies...${NC}\n"
    
    echo -e "${BLUE}[*] Updating package lists...${NC}"
    pkg update -y
    pkg upgrade -y
    
    echo -e "\n${BLUE}[*] Installing essential packages...${NC}"
    PACKAGES="python python3 wireless-tools root-repo tsu"
    
    for package in $PACKAGES; do
        echo -e "${CYAN}[*] Installing $package...${NC}"
        pkg install $package -y 2>/dev/null || echo -e "${YELLOW}[!] Could not install $package${NC}"
    done
    
    # Install Python packages
    echo -e "\n${BLUE}[*] Installing Python packages...${NC}"
    if command -v pip3 &> /dev/null; then
        pip3 install pyfiglet psutil 2>/dev/null || echo -e "${YELLOW}[!] Some Python packages failed${NC}"
    elif command -v pip &> /dev/null; then
        pip install pyfiglet psutil 2>/dev/null || echo -e "${YELLOW}[!] Some Python packages failed${NC}"
    fi
    
    echo -e "\n${GREEN}[+] Dependencies installed successfully!${NC}"
}

# Install WiFiT
install_wifit() {
    echo -e "\n${YELLOW}[*] Installing WiFiT...${NC}"
    
    # Get script directory - handle both direct run and piped from curl
    if [ -n "${BASH_SOURCE[0]}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
        SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    else
        # If piped from curl, assume we're in the WiFiT directory
        if [ -f "wifit.py" ]; then
            SCRIPT_DIR="$(pwd)"
        else
            echo -e "${RED}[-] Error: wifit.py not found!${NC}"
            echo -e "${YELLOW}[!] Please run this script from the WiFiT directory${NC}"
            echo -e "${YELLOW}[!] Or clone first: git clone https://github.com/TuHiN22/WiFiT.git${NC}"
            exit 1
        fi
    fi
    
    echo -e "${BLUE}[*] Source directory: $SCRIPT_DIR${NC}"
    
    # For Termux, install to $PREFIX/bin
    if [ -d "/data/data/com.termux" ]; then
        INSTALL_DIR="$PREFIX/bin"
    else
        INSTALL_DIR="/usr/local/bin"
    fi
    
    echo -e "${BLUE}[*] Installation directory: $INSTALL_DIR${NC}"
    
    # Verify source file exists
    if [ ! -f "$SCRIPT_DIR/wifit.py" ]; then
        echo -e "${RED}[-] Error: $SCRIPT_DIR/wifit.py not found!${NC}"
        exit 1
    fi
    
    # Copy main script
    echo -e "${BLUE}[*] Copying WiFiT script...${NC}"
    
    # First, copy the actual Python script
    cp "$SCRIPT_DIR/wifit.py" "$INSTALL_DIR/wifit.py"
    chmod +x "$INSTALL_DIR/wifit.py"
    
    # Then create wrapper script
    cat > "$INSTALL_DIR/wifit" << 'EOF'
#!/bin/bash
# WiFiT Wrapper Script - Auto elevates to root

# Check for wifit.py in installation directory
if [ -f "$PREFIX/bin/wifit.py" ]; then
    WIFIT_SCRIPT="$PREFIX/bin/wifit.py"
elif [ -f "/usr/local/bin/wifit.py" ]; then
    WIFIT_SCRIPT="/usr/local/bin/wifit.py"
else
    echo "[-] WiFiT script not found!"
    exit 1
fi

# Run with python3
python3 "$WIFIT_SCRIPT" "$@"
EOF
    
    chmod +x "$INSTALL_DIR/wifit"
    
    # Create reports directory
    mkdir -p "$SCRIPT_DIR/reports"
    
    echo -e "${GREEN}[+] WiFiT installed successfully!${NC}"
}

# Check installation
check_installation() {
    echo -e "\n${YELLOW}[*] Verifying installation...${NC}\n"
    
    if command -v wifit &> /dev/null; then
        echo -e "${GREEN}[+] WiFiT command is available${NC}"
    else
        echo -e "${YELLOW}[!] WiFiT command not found in PATH${NC}"
        echo -e "${YELLOW}[!] You may need to restart Termux${NC}"
    fi
    
    # Check dependencies
    echo -e "\n${BLUE}[*] Checking dependencies:${NC}"
    
    command -v python3 &> /dev/null && echo -e "${GREEN}  ✓ Python 3${NC}" || echo -e "${RED}  ✗ Python 3${NC}"
    command -v tsu &> /dev/null && echo -e "${GREEN}  ✓ tsu (root access)${NC}" || echo -e "${YELLOW}  ! tsu (install with: pkg install tsu)${NC}"
    
    # Check root access
    echo -e "\n${BLUE}[*] Checking root access:${NC}"
    if tsu -c "id" 2>/dev/null | grep -q "uid=0"; then
        echo -e "${GREEN}  ✓ Root access available${NC}"
    else
        echo -e "${YELLOW}  ! Root access not configured${NC}"
        echo -e "${YELLOW}  ! Install Magisk or KernelSU for root${NC}"
    fi
}

# Show usage
show_usage() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                       Usage Guide                           ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}To run WiFiT:${NC}"
    echo -e "  ${YELLOW}wifit${NC}  ${BLUE}(no sudo needed!)${NC}"
    echo ""
    echo -e "${GREEN}First time setup:${NC}"
    echo -e "  1. Grant Termux root permission in Magisk/KernelSU"
    echo -e "  2. Run: ${YELLOW}tsu${NC} (grant root when prompted)"
    echo -e "  3. Then run: ${YELLOW}wifit${NC}"
    echo ""
    echo -e "${GREEN}Features:${NC}"
    echo -e "  • Auto Attack - Automatically scan and attack WPS networks"
    echo -e "  • Pixie Dust - Fast WPS PIN recovery"
    echo -e "  • Brute Force - Systematic PIN testing"
    echo -e "  • Smart Attack - AI-enhanced recovery"
    echo -e "  • Root Fix - Fix superuser access issues"
    echo ""
    echo -e "${BLUE}GitHub: https://github.com/TuHiN22/WiFiT${NC}"
    echo ""
}

# Main installation process
main() {
    show_banner
    
    echo -e "${CYAN}[*] Starting WiFiT installation...${NC}\n"
    
    # Check if wifit.py exists in current directory
    if [ ! -f "wifit.py" ]; then
        echo -e "${YELLOW}[!] wifit.py not found in current directory${NC}"
        echo -e "${YELLOW}[!] Cloning from GitHub...${NC}\n"
        
        if command -v git &> /dev/null; then
            git clone https://github.com/TuHiN22/WiFiT.git
            cd WiFiT || exit 1
        else
            echo -e "${RED}[-] Git not installed. Installing...${NC}"
            pkg install git -y
            git clone https://github.com/TuHiN22/WiFiT.git
            cd WiFiT || exit 1
        fi
    fi
    
    check_termux
    echo ""
    
    install_dependencies_termux
    echo ""
    
    install_wifit
    echo ""
    
    check_installation
    echo ""
    
    show_usage
    
    echo -e "${GREEN}[+] Installation complete!${NC}"
    echo -e "${YELLOW}[*] Run 'wifit' to start (no sudo needed!)${NC}"
    echo ""
}

# Run main installation
main
