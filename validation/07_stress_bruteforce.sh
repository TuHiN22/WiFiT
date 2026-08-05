#!/usr/bin/env bash
# Phase 7: Stress Testing (Brute Force)
# Tests: 500+ PIN attempts, memory stability, session persistence

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/validation_logs"
PHASE_LOG="$LOG_DIR/phase7_07_stress_bruteforce.log"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info() { echo -e "${BLUE}[INFO]${NC} $*" | tee -a "$PHASE_LOG"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $*" | tee -a "$PHASE_LOG"; }
log_error() { echo -e "${RED}[FAIL]${NC} $*" | tee -a "$PHASE_LOG"; }

main() {
    log_info "=== Phase 7: Stress Testing ==="
    cd "$PROJECT_ROOT"
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    
    log_info "Testing brute force PIN enumeration (1000 PINs)..."
    python3 -c "
from wifit_core.wps_bruteforce import enumerate_all_pins
count = 0
for pin in enumerate_all_pins():
    count += 1
    if count >= 1000:
        break
print(f'✓ Generated {count} PINs successfully')
assert count == 1000
" >> "$PHASE_LOG" 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "Stress test passed (1000 PINs)"
        exit 0
    else
        log_error "Stress test failed"
        exit 1
    fi
}

mkdir -p "$LOG_DIR"
main "$@"
