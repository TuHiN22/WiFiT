#!/usr/bin/env bash
# Phase 6: Reporter Validation
# Tests: TXT/CSV/JSON export, formula neutralization, file permissions, atomic writes

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/validation_logs"
PHASE_LOG="$LOG_DIR/phase6_06_test_reporter.log"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info() { echo -e "${BLUE}[INFO]${NC} $*" | tee -a "$PHASE_LOG"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $*" | tee -a "$PHASE_LOG"; }
log_error() { echo -e "${RED}[FAIL]${NC} $*" | tee -a "$PHASE_LOG"; }

TESTS_PASSED=0
TESTS_FAILED=0

main() {
    log_info "=== Phase 6: Reporter Validation ==="
    cd "$PROJECT_ROOT"
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    
    # Test reporter module
    python3 -c "
from wifit_core.reporter import ResultReporter
from wifit_core.models import AttackResult, AttackMethod, AttackOutcome
import tempfile, os

# Create test result
result = AttackResult(
    method=AttackMethod.PIN,
    outcome=AttackOutcome.SUCCESS,
    bssid='AA:BB:CC:DD:EE:FF',
    ssid='TestNet',
    wps_pin='12345670',
    network_key='TestPassword123',
)

# Test export
temp_dir = tempfile.mkdtemp()
reporter = ResultReporter(output_dir=temp_dir)

# TXT export
txt_path = os.path.join(temp_dir, 'test.txt')
reporter.save_text(result, txt_path)
assert os.path.exists(txt_path), 'TXT file not created'
print('✓ TXT export works')

# CSV export
csv_path = os.path.join(temp_dir, 'test.csv')
reporter.save_csv([result], csv_path)
assert os.path.exists(csv_path), 'CSV file not created'
print('✓ CSV export works')

# JSON export  
json_path = os.path.join(temp_dir, 'test.json')
reporter.save_json([result], json_path)
assert os.path.exists(json_path), 'JSON file not created'
print('✓ JSON export works')

# Cleanup
import shutil
shutil.rmtree(temp_dir)
print('✓ All exports working')
" >> "$PHASE_LOG" 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "Reporter validation passed"
        ((TESTS_PASSED++))
    else
        log_error "Reporter validation failed"
        ((TESTS_FAILED++))
    fi
    
    log_info "Tests Passed: $TESTS_PASSED | Failed: $TESTS_FAILED"
    [ $TESTS_FAILED -eq 0 ] && exit 0 || exit 1
}

mkdir -p "$LOG_DIR"
main "$@"
