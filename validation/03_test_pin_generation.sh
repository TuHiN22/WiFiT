#!/bin/bash
#
# Phase 3: PIN Generation Validation
# Tests all 30 PIN algorithms for given BSSID
#

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <BSSID>"
    exit 1
fi

TARGET_BSSID="$1"

echo "[Phase 3] Testing PIN generation for $TARGET_BSSID..."

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Create test script
TEST_SCRIPT=$(mktemp)
cat > "$TEST_SCRIPT" << 'EOFPYTHON'
import sys
import json
from wifit_core.pin_generator import PINGenerator, wps_checksum

bssid = sys.argv[1]
output_file = sys.argv[2]

print(f"Generating PINs for BSSID: {bssid}")

try:
    generator = PINGenerator()
    
    # Get all algorithms
    all_pins = generator.get_all(bssid, include_static=True)
    
    print(f"✓ Generated {len(all_pins)} PINs from {len(set(algo for algo, _ in all_pins))} algorithms")
    
    # Verify checksums
    invalid_checksums = []
    for algo_id, pin in all_pins:
        if pin and pin != "":  # Skip empty PIN
            if len(pin) != 8:
                invalid_checksums.append((algo_id, pin, "wrong length"))
            else:
                pin_7digit = int(pin[:7])
                expected_checksum = wps_checksum(pin_7digit)
                if int(pin[7]) != expected_checksum:
                    invalid_checksums.append((algo_id, pin, "checksum mismatch"))
    
    if invalid_checksums:
        print(f"✗ Found {len(invalid_checksums)} PINs with invalid checksums:")
        for algo, pin, reason in invalid_checksums:
            print(f"  - {algo}: {pin} ({reason})")
        sys.exit(1)
    else:
        print("✓ All PINs have valid checksums")
    
    # Get suggested PINs
    suggested = generator.get_suggested(bssid)
    print(f"✓ Suggested {len(suggested)} PINs for this MAC")
    
    # Show first 10 suggested
    print("\nTop 10 suggested PINs:")
    for i, (algo_id, pin) in enumerate(suggested[:10], 1):
        pin_display = pin if pin else "<empty>"
        print(f"  {i:2d}. {algo_id:20s}: {pin_display}")
    
    # Check for duplicates in suggested
    unique_pins = set(pin for _, pin in suggested if pin)
    if len(unique_pins) < len([p for _, p in suggested if p]):
        print(f"✗ Warning: Duplicate PINs in suggested list")
    else:
        print(f"✓ No duplicates in suggested PINs")
    
    # Save results
    results = {
        "bssid": bssid,
        "total_algorithms": len(all_pins),
        "suggested_count": len(suggested),
        "all_pins": [{"algorithm": algo, "pin": pin} for algo, pin in all_pins],
        "suggested_pins": [{"algorithm": algo, "pin": pin} for algo, pin in suggested],
        "validation": {
            "checksums_valid": len(invalid_checksums) == 0,
            "no_duplicates": len(unique_pins) == len([p for _, p in suggested if p])
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Results saved to {output_file}")
    sys.exit(0)
    
except Exception as e:
    print(f"✗ PIN generation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOFPYTHON

# Run PIN generation test
OUTPUT_FILE="$REPO_ROOT/validation_logs/pin_generation.json"
mkdir -p "$(dirname "$OUTPUT_FILE")"

if python3 "$TEST_SCRIPT" "$TARGET_BSSID" "$OUTPUT_FILE"; then
    echo ""
    echo "PIN generation validation: PASSED"
    rm "$TEST_SCRIPT"
    exit 0
else
    echo ""
    echo "PIN generation validation: FAILED"
    rm "$TEST_SCRIPT"
    exit 1
fi
