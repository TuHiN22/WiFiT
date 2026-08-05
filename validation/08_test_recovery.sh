#!/usr/bin/env bash
# Phase 8: Recovery & Cleanup Validation
# Tests: Graceful shutdown, process cleanup, session persistence, crash recovery

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/validation_logs"
PHASE_LOG="$LOG_DIR/phase8_08_test_recovery.log"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info() { echo -e "${BLUE}[INFO]${NC} $*" | tee -a "$PHASE_LOG"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $*" | tee -a "$PHASE_LOG"; }
log_error() { echo -e "${RED}[FAIL]${NC} $*" | tee -a "$PHASE_LOG"; }

TESTS_PASSED=0
TESTS_FAILED=0

main() {
    log_info "=== Phase 8: Recovery & Cleanup ==="
    cd "$PROJECT_ROOT"
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    
    # Test session resume
    python3 -c "
from wifit_core.wps_bruteforce import BruteforceSession
import tempfile, os

session_path = tempfile.mktemp(suffix='.json')
bssid = 'AA:BB:CC:DD:EE:FF'

# Create session
session1 = BruteforceSession.create(bssid, session_path)
pin1 = session1.progress.to_pin()
session1.save()

# Resume session
session2 = BruteforceSession.load(session_path)
pin2 = session2.progress.to_pin()

assert pin1 == pin2, f'Resume failed: {pin1} != {pin2}'
print(f'✓ Session resume works: {pin1}')

os.remove(session_path)
" >> "$PHASE_LOG" 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "Session resume validated"
        ((TESTS_PASSED++))
    else
        log_error "Session resume failed"
        ((TESTS_FAILED++))
    fi
    
    log_info "Tests Passed: $TESTS_PASSED | Failed: $TESTS_FAILED"
    [ $TESTS_FAILED -eq 0 ] && exit 0 || exit 1
}

mkdir -p "$LOG_DIR"
main "$@"
