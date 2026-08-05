#!/bin/bash
#
# Phase 2: Scanner Validation
# Tests WiFiT scanner against live networks
#

set -euo pipefail

echo "[Phase 2] Testing scanner..."

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Find wireless interface
INTERFACE=$(iw dev | awk '$1=="Interface"{print $2; exit}')
if [[ -z "$INTERFACE" ]]; then
    echo "✗ No wireless interface found"
    exit 1
fi
echo "✓ Using interface: $INTERFACE"

# Create test script
TEST_SCRIPT=$(mktemp)
cat > "$TEST_SCRIPT" << 'EOFPYTHON'
import sys
import json
from wifit_core.scanner import WiFiScanner
from wifit_core.vulnerability import annotate_access_points

interface = sys.argv[1]
output_file = sys.argv[2]

print(f"Scanning with interface: {interface}")

try:
    scanner = WiFiScanner(interface, retries=2, timeout=15.0)
    access_points = scanner.scan()
    
    print(f"✓ Scan completed: {len(access_points)} networks found")
    
    # Annotate with vulnerability reasons
    annotated = annotate_access_points(access_points)
    
    # Statistics
    wps_count = sum(1 for ap in annotated if ap.wps)
    wpa3_count = sum(1 for ap in annotated if ap.wpa3)
    locked_count = sum(1 for ap in annotated if ap.wps_locked is True)
    
    print(f"  - WPS-enabled: {wps_count}")
    print(f"  - WPA3 networks: {wpa3_count}")
    print(f"  - WPS locked: {locked_count}")
    
    # Show first 5 results
    print("\nTop 5 networks:")
    for i, ap in enumerate(annotated[:5], 1):
        print(f"  {i}. {ap.ssid} ({ap.bssid})")
        print(f"     Signal: {ap.signal_dbm} dBm, Channel: {ap.channel}")
        if ap.wps:
            print(f"     WPS: {ap.wps_version.value if ap.wps_version else 'unknown'}, " 
                  f"Locked: {ap.wps_locked}")
            if ap.wsc_manufacturer or ap.wsc_model_name:
                print(f"     WSC: {ap.wsc_manufacturer} {ap.wsc_model_name}")
            if ap.vulnerability_reasons:
                print(f"     Vulnerabilities: {', '.join(ap.vulnerability_reasons[:2])}")
    
    # Save results
    results = {
        "scan_time": annotated[0].to_record() if annotated else None,
        "total_networks": len(annotated),
        "wps_networks": wps_count,
        "wpa3_networks": wpa3_count,
        "locked_networks": locked_count,
        "networks": [ap.to_record() for ap in annotated[:10]]  # First 10
    }
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Results saved to {output_file}")
    sys.exit(0)
    
except Exception as e:
    print(f"✗ Scanner failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOFPYTHON

# Run scanner test
OUTPUT_FILE="$REPO_ROOT/validation_logs/scanner_results.json"
mkdir -p "$(dirname "$OUTPUT_FILE")"

if python3 "$TEST_SCRIPT" "$INTERFACE" "$OUTPUT_FILE"; then
    echo ""
    echo "Scanner validation: PASSED"
    rm "$TEST_SCRIPT"
    exit 0
else
    echo ""
    echo "Scanner validation: FAILED"
    rm "$TEST_SCRIPT"
    exit 1
fi
