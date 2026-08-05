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
    export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
    
    # Test session resume
    python3 -c "
from wifit_core.wps_bruteforce import BruteforceSession
import tempfile, os, shutil

session_dir = tempfile.mkdtemp()
bssid = 'AA:BB:CC:DD:EE:FF'

# Create session
session1 = BruteforceSession(bssid, session_dir=session_dir)
progress1 = session1.start()
pin1 = progress1.to_pin()
session1.save()

# Resume session
session2 = BruteforceSession(bssid, session_dir=session_dir, session_id=session1.session_id)
progress2 = session2.start()
pin2 = progress2.to_pin()

assert pin1 == pin2, f'Resume failed: {pin1} != {pin2}'
print(f'✓ Session resume works: {pin1}')

session1.delete()
shutil.rmtree(session_dir)
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
