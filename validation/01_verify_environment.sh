#!/bin/bash
#
# Phase 1: Environment Verification
# Verifies root access, Python version, required packages, and wireless interface
#

set -euo pipefail

echo "[Phase 1] Verifying environment..."

# Check root
if [[ $EUID -ne 0 ]]; then
    echo "✗ Root access required"
    exit 1
fi
echo "✓ Root access confirmed (UID: $EUID)"

# Check Python version
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
    
    if [[ $PYTHON_MAJOR -ge 3 ]] && [[ $PYTHON_MINOR -ge 10 ]]; then
        echo "✓ Python $PYTHON_VERSION detected (>= 3.10)"
    else
        echo "✗ Python 3.10+ required, found $PYTHON_VERSION"
        exit 1
    fi
else
    echo "✗ Python 3 not found"
    exit 1
fi

# Check Termux environment (if on Android)
if [[ -d "/data/data/com.termux" ]]; then
    echo "✓ Termux environment detected"
    TERMUX=true
else
    echo "ℹ Desktop Linux environment (Termux not detected)"
    TERMUX=false
fi

# Check required commands
REQUIRED_CMDS=("iw" "ip" "grep" "awk")
for cmd in "${REQUIRED_CMDS[@]}"; do
    if command -v "$cmd" &> /dev/null; then
        echo "✓ Command available: $cmd"
    else
        echo "✗ Required command not found: $cmd"
        exit 1
    fi
done

# Check wireless interface
WIRELESS_INTERFACES=$(iw dev | awk '$1=="Interface"{print $2}')
if [[ -z "$WIRELESS_INTERFACES" ]]; then
    echo "✗ No wireless interfaces detected"
    echo "  Run 'iw dev' to check available interfaces"
    exit 1
fi

echo "✓ Wireless interfaces found:"
for iface in $WIRELESS_INTERFACES; do
    echo "  - $iface"
done

# Check WiFiT installation
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -d "$REPO_ROOT/wifit_core" ]]; then
    echo "✓ wifit_core package found at $REPO_ROOT/wifit_core"
else
    echo "✗ wifit_core package not found"
    exit 1
fi

# Check Python can import wifit_core
cd "$REPO_ROOT"
if python3 -c "import wifit_core; print(f'wifit_core version: {wifit_core.__version__}')" 2>/dev/null; then
    echo "✓ wifit_core importable"
else
    echo "✗ Cannot import wifit_core"
    exit 1
fi

# Summary
echo ""
echo "Environment verification: PASSED"
echo "You can proceed with hardware validation"
exit 0
