#!/bin/bash
#
# Phase 1: Environment Verification
# Verifies root availability, Python, required commands, and wireless hardware.
#

set -euo pipefail

echo "[Phase 1] Verifying environment..."

find_root_runner() {
    local candidate

    if [[ -n "${PREFIX:-}" ]]; then
        candidate="$PREFIX/bin/sudo"
        if [[ -f "$candidate" && -x "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    fi

    candidate="$(command -v sudo 2>/dev/null || true)"
    if [[ -n "$candidate" && -f "$candidate" && -x "$candidate" ]]; then
        printf '%s\n' "$candidate"
        return 0
    fi

    return 1
}

ROOT_RUNNER=""
if [[ $EUID -eq 0 ]]; then
    echo "✓ Root access confirmed (UID: $EUID)"
else
    ROOT_RUNNER="$(find_root_runner || true)"
    if [[ -z "$ROOT_RUNNER" ]]; then
        echo "✗ One-shot root command not found"
        echo "  Install it with: pkg install root-repo tsu"
        exit 1
    fi

    ID_BIN="$(command -v id 2>/dev/null || true)"
    if [[ -z "$ID_BIN" ]]; then
        echo "✗ Required command not found: id"
        exit 1
    fi

    if ROOT_UID="$("$ROOT_RUNNER" "$ID_BIN" -u 2>/dev/null)" && [[ "$ROOT_UID" == "0" ]]; then
        echo "✓ One-shot root access confirmed"
    else
        echo "✗ Root permission was not granted through $ROOT_RUNNER"
        echo "  Verify with: sudo id"
        exit 1
    fi
fi

if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
else
    echo "✗ Python 3 not found"
    exit 1
fi

PYTHON_VERSION="$($PYTHON_BIN --version 2>&1 | awk '{print $2}')"
if "$PYTHON_BIN" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
    echo "✓ Python $PYTHON_VERSION detected (>= 3.10)"
else
    echo "✗ Python 3.10+ required, found $PYTHON_VERSION"
    exit 1
fi

if [[ -d "/data/data/com.termux" ]]; then
    echo "✓ Termux environment detected"
else
    echo "ℹ Desktop Linux environment (Termux not detected)"
fi

REQUIRED_CMDS=("iw" "ip" "grep" "awk")
for cmd in "${REQUIRED_CMDS[@]}"; do
    if command -v "$cmd" >/dev/null 2>&1; then
        echo "✓ Command available: $cmd"
    else
        echo "✗ Required command not found: $cmd"
        exit 1
    fi
done

IW_BIN="$(command -v iw)"
if [[ $EUID -eq 0 ]]; then
    if ! IW_OUTPUT="$("$IW_BIN" dev 2>&1)"; then
        echo "✗ Unable to query wireless interfaces"
        printf '  %s\n' "$IW_OUTPUT"
        exit 1
    fi
else
    if ! IW_OUTPUT="$("$ROOT_RUNNER" "$IW_BIN" dev 2>&1)"; then
        echo "✗ Unable to query wireless interfaces with root access"
        printf '  %s\n' "$IW_OUTPUT"
        exit 1
    fi
fi

WIRELESS_INTERFACES="$(awk '$1=="Interface"{print $2}' <<< "$IW_OUTPUT")"
if [[ -z "$WIRELESS_INTERFACES" ]]; then
    echo "✗ No wireless interfaces detected"
    echo "  Run 'sudo iw dev' to inspect the device state"
    exit 1
fi

echo "✓ Wireless interfaces found:"
while IFS= read -r iface; do
    [[ -n "$iface" ]] && echo "  - $iface"
done <<< "$WIRELESS_INTERFACES"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -d "$REPO_ROOT/wifit_core" ]]; then
    echo "✓ wifit_core package found at $REPO_ROOT/wifit_core"
else
    echo "✗ wifit_core package not found"
    exit 1
fi

export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
if "$PYTHON_BIN" -c "import wifit_core; print(f'wifit_core version: {wifit_core.__version__}')"; then
    echo "✓ wifit_core importable"
else
    echo "✗ Cannot import wifit_core"
    exit 1
fi

if "$PYTHON_BIN" -c 'import pytest' >/dev/null 2>&1; then
    echo "✓ pytest available"
else
    echo "ℹ pytest is not installed; add it with: python -m pip install -e '.[test]'"
fi

echo ""
echo "Environment verification: PASSED"
echo "You can proceed with hardware validation"
