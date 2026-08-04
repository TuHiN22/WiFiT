#!/bin/bash
#
# WiFiT Installation Script
# Author: TuHiN
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
    echo "║                    WiFiT Installer v1.0                     ║"
    echo "║              Professional WPS Testing Toolkit                ║"
    echo "║                      Author: TuHiN                           ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}[-] Please run this script as root${NC}"
        exit 1
    fi
}

# Install dependencies
install_dependencies() {
    echo -e "${YELLOW}[*] Installing dependencies...${NC}"
    
    # Detect package manager
    if command -v apt-get &> /dev/null; then
        PKG_MANAGER="apt-get"
        UPDATE_CMD="apt-get update"
        INSTALL_CMD="apt-get install -y"
    elif command -v pkg &> /dev/null; then
        # Termux
        PKG_MANAGER="pkg"
        UPDATE_CMD="pkg update -y"
        INSTALL_CMD="pkg install -y"
    elif command -v yum &> /dev/null; then
        PKG_MANAGER="yum"
        UPDATE_CMD="yum update -y"
        INSTALL_CMD="yum install -y"
    else
        echo -e "${RED}[-] Unsupported package manager${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}[*] Updating package lists...${NC}"
    $UPDATE_CMD
    
    echo -e "${BLUE}[*] Installing required packages...${NC}"
    
    # Common packages
    PACKAGES="python python3 wireless-tools"
    
    # Additional packages based on system
    if [ "$PKG_MANAGER" == "apt-get" ]; then
        PACKAGES="$PACKAGES wpasupplicant pixiewps iw"
    elif [ "$PKG_MANAGER" == "pkg" ]; then
        # Termux
        PACKAGES="$PACKAGES root-repo tsu"
    fi
    
    for package in $PACKAGES; do
        echo -e "${CYAN}[*] Installing $package...${NC}"
        $INSTALL_CMD $package 2>/dev/null || echo -e "${YELLOW}[!] Could not install $package (may not be available)${NC}"
    done
    
    # Install Python packages
    echo -e "${BLUE}[*] Installing Python packages...${NC}"
    if command -v pip3 &> /dev/null; then
        pip3 install pyfiglet psutil 2>/dev/null || echo -e "${YELLOW}[!] Some Python packages failed to install${NC}"
    elif command -v pip &> /dev/null; then
        pip install pyfiglet psutil 2>/dev/null || echo -e "${YELLOW}[!] Some Python packages failed to install${NC}"
    fi
    
    echo -e "${GREEN}[+] Dependencies installed successfully!${NC}"
}

# Install WiFiT
install_wifit() {
    echo -e "${YELLOW}[*] Installing WiFiT...${NC}"
    
    # Get installation directory
    INSTALL_DIR="/usr/local/bin"
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    
    # Copy main script
    echo -e "${BLUE}[*] Copying WiFiT script...${NC}"
    cp "$SCRIPT_DIR/wifit.py" "$INSTALL_DIR/wifit"
    chmod +x "$INSTALL_DIR/wifit"
    
    # Create symbolic link
    ln -sf "$INSTALL_DIR/wifit" /usr/bin/wifit 2>/dev/null || true
    
    # Create reports directory
    mkdir -p "$SCRIPT_DIR/reports"
    
    echo -e "${GREEN}[+] WiFiT installed successfully!${NC}"
}

# Check installation
check_installation() {
    echo -e "${YELLOW}[*] Verifying installation...${NC}"
    
    if command -v wifit &> /dev/null; then
        echo -e "${GREEN}[+] WiFiT command is available${NC}"
    else
        echo -e "${YELLOW}[!] WiFiT command not found in PATH${NC}"
        echo -e "${YELLOW}[!] You may need to run: source ~/.bashrc${NC}"
    fi
    
    # Check dependencies
    echo -e "${BLUE}[*] Checking dependencies:${NC}"
    
    command -v python3 &> /dev/null && echo -e "${GREEN}  ✓ Python 3${NC}" || echo -e "${RED}  ✗ Python 3${NC}"
    command -v wpa_supplicant &> /dev/null && echo -e "${GREEN}  ✓ wpa_supplicant${NC}" || echo -e "${YELLOW}  ! wpa_supplicant (optional)${NC}"
    command -v pixiewps &> /dev/null && echo -e "${GREEN}  ✓ pixiewps${NC}" || echo -e "${YELLOW}  ! pixiewps (optional)${NC}"
    command -v iw &> /dev/null && echo -e "${GREEN}  ✓ iw${NC}" || echo -e "${YELLOW}  ! iw (optional)${NC}"
}

# Show usage
show_usage() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                       Usage Guide                           ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}To run WiFiT:${NC}"
    echo -e "  ${YELLOW}sudo wifit${NC}"
    echo ""
    echo -e "${GREEN}Features:${NC}"
    echo -e "  • Auto Attack - Automatically scan and attack WPS networks"
    echo -e "  • Pixie Dust - Fast WPS PIN recovery"
    echo -e "  • Brute Force - Systematic PIN testing"
    echo -e "  • Smart Attack - AI-enhanced recovery"
    echo -e "  • View Saved Passwords"
    echo ""
    echo -e "${BLUE}GitHub: https://github.com/TuHiN22/WiFiT${NC}"
    echo ""
}

# Main installation process
main() {
    show_banner
    check_root
    
    echo -e "${CYAN}[*] Starting WiFiT installation...${NC}"
    echo ""
    
    install_dependencies
    echo ""
    
    install_wifit
    echo ""
    
    check_installation
    echo ""
    
    show_usage
    
    echo -e "${GREEN}[+] Installation complete!${NC}"
    echo -e "${YELLOW}[*] Run 'sudo wifit' to start${NC}"
    echo ""
}

# Run main installation
main
