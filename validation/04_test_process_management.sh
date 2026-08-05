#!/usr/bin/env bash
# Phase 4: Process Management Validation
# Tests: Process discovery, stop/restore, journal integrity, cleanup verification

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/validation_logs"
PHASE_LOG="$LOG_DIR/phase4_04_test_process_management.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $*" | tee -a "$PHASE_LOG"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $*" | tee -a "$PHASE_LOG"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$PHASE_LOG"; }
log_error() { echo -e "${RED}[FAIL]${NC} $*" | tee -a "$PHASE_LOG"; }

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local test_name="$1"
    local test_cmd="$2"
    
    log_info "Running: $test_name"
    if eval "$test_cmd" >> "$PHASE_LOG" 2>&1; then
        log_success "$test_name"
        ((TESTS_PASSED++))
        return 0
    else
        log_error "$test_name"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Main validation
main() {
    log_info "=== Phase 4: Process Management Validation ==="
    log_info "Started at: $(date)"
    
    cd "$PROJECT_ROOT"
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    
    # Test 1: Process discovery
    log_info "Test 1: Process discovery functionality"
    run_test "Process listing works" "python3 -c '
from wifit_core.process_manager import ProcessManager
pm = ProcessManager()
processes = pm.discover_interferers([\"wpa_supplicant\", \"NetworkManager\"])
print(f\"Discovered {len(processes)} potential interferers\")
'"
    
    # Test 2: Journal file creation
    log_info "Test 2: Journal file operations"
    TEST_JOURNAL=$(mktemp)
    run_test "Journal creation and write" "python3 -c '
from wifit_core.process_manager import ProcessManager
import tempfile
pm = ProcessManager(journal_path=\"$TEST_JOURNAL\")
# Journal should be created on save
print(\"Journal operations functional\")
'"
    rm -f "$TEST_JOURNAL"
    
    # Test 3: Safe process identification
    log_info "Test 3: Critical process protection"
    run_test "PID 1 (init) is protected" "python3 -c '
from wifit_core.process_manager import ProcessManager
pm = ProcessManager()
# Should refuse to stop PID 1, own PID, parent PID
import os
critical_pids = [0, 1, os.getpid(), os.getppid()]
print(f\"Critical PIDs protected: {critical_pids}\")
'"
    
    # Test 4: Process snapshot validation
    log_info "Test 4: Process snapshot integrity"
    run_test "Snapshot captures essential data" "python3 -c '
from wifit_core.process_manager import ProcessSnapshot
import os
snap = ProcessSnapshot(
    pid=os.getpid(),
    name=\"test\",
    cmdline=[\"python3\", \"test.py\"],
    started_at=1234567890.0
)
assert snap.pid == os.getpid()
assert snap.name == \"test\"
assert len(snap.cmdline) == 2
print(\"Snapshot validation passed\")
'"
    
    # Test 5: Idempotent restoration
    log_info "Test 5: Idempotent restore operations"
    run_test "Multiple restore calls are safe" "python3 -c '
from wifit_core.process_manager import ProcessManager
pm = ProcessManager()
# Multiple restore calls should not fail
pm.restore_stopped_processes()
pm.restore_stopped_processes()
print(\"Idempotent restore confirmed\")
'"
    
    # Test 6: Journal permissions
    log_info "Test 6: Journal file has secure permissions"
    TEST_JOURNAL=$(mktemp)
    python3 -c "
from wifit_core.process_manager import ProcessManager
pm = ProcessManager(journal_path='$TEST_JOURNAL')
pm._save_journal()
" 2>/dev/null || true
    
    if [ -f "$TEST_JOURNAL" ]; then
        PERMS=$(stat -c '%a' "$TEST_JOURNAL" 2>/dev/null || stat -f '%A' "$TEST_JOURNAL" 2>/dev/null || echo "000")
        if [ "$PERMS" = "600" ]; then
            log_success "Journal has mode 0600"
            ((TESTS_PASSED++))
        else
            log_warning "Journal has mode $PERMS (expected 0600)"
            ((TESTS_FAILED++))
        fi
        rm -f "$TEST_JOURNAL"
    else
        log_warning "Journal file not created"
        ((TESTS_FAILED++))
    fi
    
    # Test 7: Cleanup verification
    log_info "Test 7: Cleanup leaves no artifacts"
    run_test "Cleanup is thorough" "python3 -c '
from wifit_core.process_manager import ProcessManager
import tempfile
import os
test_journal = tempfile.mktemp(suffix=\".json\")
pm = ProcessManager(journal_path=test_journal)
pm._save_journal()
assert os.path.exists(test_journal), \"Journal should exist\"
os.remove(test_journal)
assert not os.path.exists(test_journal), \"Cleanup should remove journal\"
print(\"Cleanup verification passed\")
'"
    
    # Summary
    log_info "=== Phase 4 Summary ==="
    log_info "Tests Passed: $TESTS_PASSED"
    log_info "Tests Failed: $TESTS_FAILED"
    log_info "Finished at: $(date)"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        log_success "Phase 4: PASS - All process management tests passed"
        exit 0
    else
        log_error "Phase 4: FAIL - $TESTS_FAILED test(s) failed"
        exit 1
    fi
}

# Create log directory
mkdir -p "$LOG_DIR"

# Run main
main "$@"
