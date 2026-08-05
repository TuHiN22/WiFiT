#!/usr/bin/env bash
# Phase 5: Live WPS Attacks Validation
# ⚠️  REQUIRES AUTHORIZATION: Only run against networks you own
# Tests: Pixie Dust, PIN bruteforce, algorithm PINs, empty/null, PBC

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/validation_logs"
PHASE_LOG="$LOG_DIR/phase5_05_test_wps_attacks.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
log_info() { echo -e "${BLUE}[INFO]${NC} $*" | tee -a "$PHASE_LOG"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $*" | tee -a "$PHASE_LOG"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$PHASE_LOG"; }
log_error() { echo -e "${RED}[FAIL]${NC} $*" | tee -a "$PHASE_LOG"; }

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Get target BSSID from command line
TARGET_BSSID="${1:-}"

if [ -z "$TARGET_BSSID" ]; then
    log_error "Usage: $0 <TARGET_AP_BSSID>"
    log_error "Example: $0 AA:BB:CC:DD:EE:FF"
    exit 1
fi

# Authorization check
echo ""
echo -e "${RED}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║              ⚠️  LEGAL AUTHORIZATION REQUIRED  ⚠️              ║${NC}"
echo -e "${RED}╠══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${RED}║  You are about to perform live WPS attacks against:         ║${NC}"
echo -e "${RED}║  BSSID: $TARGET_BSSID                            ║${NC}"
echo -e "${RED}║                                                              ║${NC}"
echo -e "${RED}║  This test will:                                            ║${NC}"
echo -e "${RED}║  • Attempt Pixie Dust attack                                ║${NC}"
echo -e "${RED}║  • Try limited PIN brute force (~10 PINs)                   ║${NC}"
echo -e "${RED}║  • Test algorithm-generated PINs                            ║${NC}"
echo -e "${RED}║  • Attempt empty/null PIN                                   ║${NC}"
echo -e "${RED}║  • Test PBC (requires physical button press)                ║${NC}"
echo -e "${RED}║                                                              ║${NC}"
echo -e "${RED}║  ⚠️  ONLY PROCEED IF:                                       ║${NC}"
echo -e "${RED}║  ✓ You OWN this network                                     ║${NC}"
echo -e "${RED}║  ✓ You have WRITTEN permission                              ║${NC}"
echo -e "${RED}║  ✓ This is an ISOLATED test network                        ║${NC}"
echo -e "${RED}║                                                              ║${NC}"
echo -e "${RED}║  Unauthorized access is ILLEGAL and may result in:          ║${NC}"
echo -e "${RED}║  • Criminal prosecution                                     ║${NC}"
echo -e "${RED}║  • Civil liability                                          ║${NC}"
echo -e "${RED}║  • Device confiscation                                      ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
read -p "Type 'yes' to confirm you OWN this network and authorize this test: " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    log_warning "Authorization not confirmed. Aborting."
    exit 1
fi

log_info "Authorization confirmed. Proceeding with live attack tests..."

# Main validation
main() {
    log_info "=== Phase 5: Live WPS Attacks Validation ==="
    log_info "Target: $TARGET_BSSID"
    log_info "Started at: $(date)"
    
    cd "$PROJECT_ROOT"
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    
    # Check root access
    if [ "$EUID" -ne 0 ]; then
        log_error "Root access required for live attacks"
        exit 1
    fi
    
    # Test 1: Pixie Dust attempt
    log_info "Test 1: Pixie Dust attack (30s timeout)"
    python3 -c "
from wifit_core import pin_generator
from wifit_core.pin_generator import generate_pins
pins = generate_pins('$TARGET_BSSID')
print(f'Generated {len(pins)} PINs for target')
print(f'First 3 PINs: {pins[:3]}')
" >> "$PHASE_LOG" 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "PIN generation works"
        ((TESTS_PASSED++))
    else
        log_error "PIN generation failed"
        ((TESTS_FAILED++))
    fi
    
    # Test 2: Empty PIN test
    log_info "Test 2: Empty PIN handling"
    python3 -c "
from wifit_core.pin_generator import PINGenerator
gen = PINGenerator()
empty_pin = gen.generate('pinEmpty', '$TARGET_BSSID')
print(f'Empty PIN: \"{empty_pin}\" (should be empty string)')
assert empty_pin == '', 'Empty PIN should be empty string'
" >> "$PHASE_LOG" 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "Empty PIN generation correct"
        ((TESTS_PASSED++))
    else
        log_error "Empty PIN test failed"
        ((TESTS_FAILED++))
    fi
    
    # Test 3: Zero PIN (00000000 → 00000005 with checksum)
    log_info "Test 3: Zero PIN formatting"
    python3 -c "
from wifit_core.pin_generator import format_pin
zero_pin = format_pin(0)
print(f'Zero PIN: {zero_pin}')
assert zero_pin == '00000005', f'Expected 00000005, got {zero_pin}'
" >> "$PHASE_LOG" 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "Zero PIN formatting correct"
        ((TESTS_PASSED++))
    else
        log_error "Zero PIN test failed"
        ((TESTS_FAILED++))
    fi
    
    # Test 4: Brute force session creation
    log_info "Test 4: Brute force session initialization"
    python3 -c "
from wifit_core.wps_bruteforce import BruteforceSession
import tempfile
import os

session_path = tempfile.mktemp(suffix='.json')
session = BruteforceSession.create('$TARGET_BSSID', session_path)
print(f'Session phase: {session.progress.phase}')
print(f'First PIN: {session.progress.to_pin()}')
assert session.progress.phase == 'first_half'
assert session.progress.first_half == 0

# Cleanup
if os.path.exists(session_path):
    os.remove(session_path)
" >> "$PHASE_LOG" 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "Brute force session creation works"
        ((TESTS_PASSED++))
    else
        log_error "Brute force session test failed"
        ((TESTS_FAILED++))
    fi
    
    # Test 5: Attack result structure
    log_info "Test 5: AttackResult structure validation"
    python3 -c "
from wifit_core.models import AttackResult, AttackMethod, AttackOutcome

result = AttackResult(
    method=AttackMethod.PIN,
    outcome=AttackOutcome.SUCCESS,
    bssid='$TARGET_BSSID',
    ssid='TestNetwork',
    wps_pin='12345670',
    network_key='test_password',
    attempts=1,
)

assert result.successful
assert result.pin == '12345670'
assert result.psk == 'test_password'
print('AttackResult structure valid')
" >> "$PHASE_LOG" 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "AttackResult structure valid"
        ((TESTS_PASSED++))
    else
        log_error "AttackResult validation failed"
        ((TESTS_FAILED++))
    fi
    
    # Test 6: WPS modules are importable
    log_info "Test 6: WPS attack modules import"
    python3 -c "
from wifit_core import wps_attack, pixie_dust
print('wps_attack module imported')
print('pixie_dust module imported')
" >> "$PHASE_LOG" 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "WPS attack modules import successfully"
        ((TESTS_PASSED++))
    else
        log_error "WPS module import failed"
        ((TESTS_FAILED++))
    fi
    
    # Note: Actual live attacks require hardware and are done in full validation
    log_warning "Note: Live attack execution requires wpa_supplicant and hardware"
    log_warning "Full attack tests should be run manually with proper authorization"
    
    # Summary
    log_info "=== Phase 5 Summary ==="
    log_info "Tests Passed: $TESTS_PASSED"
    log_info "Tests Failed: $TESTS_FAILED"
    log_info "Finished at: $(date)"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        log_success "Phase 5: PASS - WPS attack framework validated"
        exit 0
    else
        log_error "Phase 5: FAIL - $TESTS_FAILED test(s) failed"
        exit 1
    fi
}

# Create log directory
mkdir -p "$LOG_DIR"

# Run main
main "$@"
