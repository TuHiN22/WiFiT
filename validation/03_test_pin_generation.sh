#!/bin/bash
#
# Phase 3: PIN Generation Validation
# Tests every available PIN algorithm for a supplied BSSID.
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

if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
else
    echo "✗ Python 3 not found"
    exit 1
fi

OUTPUT_FILE="$REPO_ROOT/validation_logs/pin_generation.json"
mkdir -p "$(dirname "$OUTPUT_FILE")"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

if "$PYTHON_BIN" - "$TARGET_BSSID" "$OUTPUT_FILE" << 'EOFPYTHON'
import json
import os
import sys

from wifit_core.pin_generator import PINGenerator, wps_checksum

bssid = sys.argv[1]
output_file = sys.argv[2]

print(f"Generating PINs for BSSID: {bssid}")

try:
    generator = PINGenerator()
    all_pins = generator.get_all(bssid, include_static=True)

    algorithm_count = len({algorithm for algorithm, _ in all_pins})
    print(f"✓ Generated {len(all_pins)} PINs from {algorithm_count} algorithms")

    invalid_checksums = []
    for algorithm_id, pin in all_pins:
        if not pin:
            continue
        if len(pin) != 8:
            invalid_checksums.append((algorithm_id, pin, "wrong length"))
            continue

        pin_7digit = int(pin[:7])
        expected_checksum = wps_checksum(pin_7digit)
        if int(pin[7]) != expected_checksum:
            invalid_checksums.append((algorithm_id, pin, "checksum mismatch"))

    if invalid_checksums:
        print(f"✗ Found {len(invalid_checksums)} PINs with invalid checksums:")
        for algorithm, pin, reason in invalid_checksums:
            print(f"  - {algorithm}: {pin} ({reason})")
        raise SystemExit(1)

    print("✓ All PINs have valid checksums")

    suggested = generator.get_suggested(bssid)
    print(f"✓ Suggested {len(suggested)} PINs for this MAC")

    print("\nTop 10 suggested PINs:")
    for index, (algorithm_id, pin) in enumerate(suggested[:10], 1):
        pin_display = pin if pin else "<empty>"
        print(f"  {index:2d}. {algorithm_id:20s}: {pin_display}")

    nonempty_suggested = [pin for _, pin in suggested if pin]
    unique_pins = set(nonempty_suggested)
    no_duplicates = len(unique_pins) == len(nonempty_suggested)
    if no_duplicates:
        print("✓ No duplicates in suggested PINs")
    else:
        print("ℹ Duplicate PIN values were produced by multiple algorithms")

    results = {
        "bssid": bssid,
        "total_algorithms": len(all_pins),
        "suggested_count": len(suggested),
        "all_pins": [
            {"algorithm": algorithm, "pin": pin} for algorithm, pin in all_pins
        ],
        "suggested_pins": [
            {"algorithm": algorithm, "pin": pin} for algorithm, pin in suggested
        ],
        "validation": {
            "checksums_valid": True,
            "no_duplicates": no_duplicates,
        },
    }

    descriptor = os.open(output_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        json.dump(results, output, indent=2)

    print(f"\n✓ Results saved to {output_file}")
except (TypeError, ValueError) as error:
    print(f"✗ PIN generation failed: {error}")
    raise SystemExit(1)
EOFPYTHON
then
    echo ""
    echo "PIN generation validation: PASSED"
else
    echo ""
    echo "PIN generation validation: FAILED"
    exit 1
fi
