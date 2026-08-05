#!/bin/bash
#
# Phase 2: Scanner Validation
# Tests WiFiT scanner against live networks.
#

set -euo pipefail

echo "[Phase 2] Testing scanner..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

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

if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
else
    echo "✗ Python 3 not found"
    exit 1
fi

IW_BIN="$(command -v iw 2>/dev/null || true)"
ENV_BIN="$(command -v env 2>/dev/null || true)"
if [[ -z "$IW_BIN" || -z "$ENV_BIN" ]]; then
    echo "✗ Required commands not found: iw and env are required"
    exit 1
fi

ROOT_RUNNER=""
if [[ $EUID -ne 0 ]]; then
    ROOT_RUNNER="$(find_root_runner || true)"
    if [[ -z "$ROOT_RUNNER" ]]; then
        echo "✗ One-shot root command not found"
        echo "  Install it with: pkg install root-repo tsu"
        exit 1
    fi
fi

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

INTERFACE="${1:-${WIFIT_INTERFACE:-}}"
if [[ -z "$INTERFACE" ]]; then
    INTERFACE="$(awk '
        $1 == "Interface" { current = $2 }
        $1 == "type" && $2 == "managed" { print current; exit }
    ' <<< "$IW_OUTPUT")"
fi
if [[ -z "$INTERFACE" ]]; then
    INTERFACE="$(awk '$1=="Interface"{print $2; exit}' <<< "$IW_OUTPUT")"
fi
if [[ -z "$INTERFACE" ]]; then
    echo "✗ No wireless interface found"
    exit 1
fi
echo "✓ Using interface: $INTERFACE"

OUTPUT_FILE="$REPO_ROOT/validation_logs/scanner_results.json"
mkdir -p "$(dirname "$OUTPUT_FILE")"

export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
PYTHON_COMMAND=("$PYTHON_BIN" - "$INTERFACE" "$OUTPUT_FILE")
if [[ $EUID -ne 0 ]]; then
    CALLER_UID="$EUID"
    CALLER_GID="$(id -g)"
    PYTHON_COMMAND=(
        "$ROOT_RUNNER"
        "$ENV_BIN"
        "PYTHONPATH=$PYTHONPATH"
        "WIFIT_OUTPUT_UID=$CALLER_UID"
        "WIFIT_OUTPUT_GID=$CALLER_GID"
        "${PYTHON_COMMAND[@]}"
    )
fi

if "${PYTHON_COMMAND[@]}" << 'EOFPYTHON'
import json
import os
import sys
from datetime import datetime, timezone

from wifit_core.scanner import WiFiScanner
from wifit_core.vulnerability import annotate_access_points

interface = sys.argv[1]
output_file = sys.argv[2]

print(f"Scanning with interface: {interface}")

try:
    scanner = WiFiScanner(interface, retries=2, timeout=15.0)
    access_points = scanner.scan()

    print(f"✓ Scan completed: {len(access_points)} networks found")
    annotated = annotate_access_points(access_points)

    wps_count = sum(1 for ap in annotated if ap.wps)
    wpa3_count = sum(1 for ap in annotated if ap.wpa3)
    locked_count = sum(1 for ap in annotated if ap.wps_locked is True)

    print(f"  - WPS-enabled: {wps_count}")
    print(f"  - WPA3 networks: {wpa3_count}")
    print(f"  - WPS locked: {locked_count}")

    print("\nTop 5 networks:")
    for index, ap in enumerate(annotated[:5], 1):
        print(f"  {index}. {ap.ssid} ({ap.bssid})")
        print(f"     Signal: {ap.signal_dbm} dBm, Channel: {ap.channel}")
        if ap.wps:
            version = ap.wps_version.value if ap.wps_version else "unknown"
            print(f"     WPS: {version}, Locked: {ap.wps_locked}")
            if ap.wsc_manufacturer or ap.wsc_model_name:
                print(f"     WSC: {ap.wsc_manufacturer} {ap.wsc_model_name}")
            if ap.vulnerability_reasons:
                print(f"     Vulnerabilities: {', '.join(ap.vulnerability_reasons[:2])}")

    results = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "total_networks": len(annotated),
        "wps_networks": wps_count,
        "wpa3_networks": wpa3_count,
        "locked_networks": locked_count,
        "networks": [ap.to_record() for ap in annotated[:10]],
    }

    descriptor = os.open(output_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        json.dump(results, output, indent=2)
    output_uid = os.environ.get("WIFIT_OUTPUT_UID")
    output_gid = os.environ.get("WIFIT_OUTPUT_GID")
    if output_uid and output_gid and hasattr(os, "chown"):
        try:
            os.chown(output_file, int(output_uid), int(output_gid))
        except OSError as error:
            print(f"ℹ Could not restore result ownership: {error}")

    print(f"\n✓ Results saved to {output_file}")
except Exception as error:
    print(f"✗ Scanner failed: {error}")
    import traceback

    traceback.print_exc()
    raise SystemExit(1)
EOFPYTHON
then
    echo ""
    echo "Scanner validation: PASSED"
else
    echo ""
    echo "Scanner validation: FAILED"
    exit 1
fi
