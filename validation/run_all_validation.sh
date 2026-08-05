#!/bin/bash
#
# WiFiT v3.0.0-rc.1 Master Hardware Validation Script
# Runs complete validation suite and generates comprehensive report
#
# Usage: sudo bash validation/run_all_validation.sh <TEST_AP_BSSID>
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOGS_DIR="$REPO_ROOT/validation_logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MASTER_LOG="$LOGS_DIR/master_run_$TIMESTAMP.log"

# Create logs directory
mkdir -p "$LOGS_DIR"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$MASTER_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$MASTER_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$MASTER_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$MASTER_LOG"
}

# Banner
show_banner() {
    cat << 'EOF' | tee -a "$MASTER_LOG"
╔══════════════════════════════════════════════════════════════╗
║        WiFiT v3.0.0-rc.1 Hardware Validation Suite         ║
╚══════════════════════════════════════════════════════════════╝
EOF
}

# Refuse to present a partial checkout as a complete validation suite.
check_phase_scripts() {
    local required_scripts=(
        "01_verify_environment.sh"
        "02_test_scanner.sh"
        "03_test_pin_generation.sh"
        "04_test_process_management.sh"
        "05_test_wps_attacks.sh"
        "06_test_reporter.sh"
        "07_stress_bruteforce.sh"
        "08_test_recovery.sh"
    )
    local missing_scripts=()
    local script_name

    for script_name in "${required_scripts[@]}"; do
        if [[ ! -f "$SCRIPT_DIR/$script_name" ]]; then
            missing_scripts+=("$script_name")
        fi
    done

    if (( ${#missing_scripts[@]} > 0 )); then
        log_error "Validation suite is incomplete; missing phase scripts:"
        for script_name in "${missing_scripts[@]}"; do
            log_error "  - $script_name"
        done
        log_error "Run the available phase scripts individually until the missing phases are implemented."
        exit 2
    fi
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Validate arguments
if [[ $# -lt 1 ]]; then
    echo "Usage: sudo bash $0 <TEST_AP_BSSID>"
    echo ""
    echo "Example: sudo bash $0 AA:BB:CC:DD:EE:FF"
    exit 1
fi

TEST_BSSID="$1"

# Initialize
show_banner
log_info "Validation started at $(date)"
log_info "Target BSSID: $TEST_BSSID"
log_info "Logs directory: $LOGS_DIR"
log_info "Master log: $MASTER_LOG"

check_phase_scripts
check_root

# Test results tracking
declare -A PHASE_RESULTS
TOTAL_PHASES=8
PASSED_PHASES=0

# Phase execution wrapper
run_phase() {
    local phase_num="$1"
    local phase_name="$2"
    local script_name="$3"
    shift 3
    local script_args=("$@")
    
    log_info ""
    log_info "=========================================="
    log_info "Phase $phase_num: $phase_name"
    log_info "=========================================="
    
    local phase_log="$LOGS_DIR/phase${phase_num}_${script_name%.sh}_$TIMESTAMP.log"
    
    if [[ -f "$SCRIPT_DIR/$script_name" ]]; then
        if bash "$SCRIPT_DIR/$script_name" "${script_args[@]}" 2>&1 | tee -a "$phase_log" "$MASTER_LOG"; then
            log_success "Phase $phase_num: $phase_name - PASSED"
            PHASE_RESULTS[$phase_num]="PASSED"
            ((PASSED_PHASES += 1))
            return 0
        else
            log_error "Phase $phase_num: $phase_name - FAILED"
            PHASE_RESULTS[$phase_num]="FAILED"
            return 1
        fi
    else
        log_warning "Phase $phase_num: Script $script_name not found - SKIPPED"
        PHASE_RESULTS[$phase_num]="SKIPPED"
        return 0
    fi
}

# Phase 1: Environment Verification
run_phase 1 "Environment Setup" "01_verify_environment.sh" || true

# Phase 2: Scanner Validation
run_phase 2 "Scanner Validation" "02_test_scanner.sh" || true

# Phase 3: PIN Generation
run_phase 3 "PIN Generation" "03_test_pin_generation.sh" "$TEST_BSSID" || true

# Phase 4: Process Management
run_phase 4 "Process Management" "04_test_process_management.sh" || true

# Phase 5: Live WPS operations
log_warning ""
log_warning "Phase 5 will perform LIVE WPS attacks on $TEST_BSSID"
read -p "Continue with live attacks? (yes/no): " -r
echo
if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    run_phase 5 "WPS Attack Validation" "05_test_wps_attacks.sh" "$TEST_BSSID" || true
else
    log_warning "Phase 5 skipped by user"
    PHASE_RESULTS[5]="SKIPPED"
fi

# Phase 6: Reporter Validation
run_phase 6 "Reporter Validation" "06_test_reporter.sh" || true

# Phase 7: Stress Testing (Optional - takes long time)
log_warning ""
log_warning "Phase 7 is stress testing and will take 1-2 hours"
read -p "Run stress tests? (yes/no): " -r
echo
if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    run_phase 7 "Stress Testing" "07_stress_bruteforce.sh" "$TEST_BSSID" 500 || true
else
    log_warning "Phase 7 skipped by user"
    PHASE_RESULTS[7]="SKIPPED"
fi

# Phase 8: Recovery & Cleanup
run_phase 8 "Recovery & Cleanup" "08_test_recovery.sh" "$TEST_BSSID" || true

# Generate Summary Report
log_info ""
log_info "=========================================="
log_info "VALIDATION SUMMARY"
log_info "=========================================="

for phase in {1..8}; do
    result="${PHASE_RESULTS[$phase]:-UNKNOWN}"
    case "$result" in
        PASSED)
            log_success "Phase $phase: $result"
            ;;
        FAILED)
            log_error "Phase $phase: $result"
            ;;
        SKIPPED)
            log_warning "Phase $phase: $result"
            ;;
        *)
            log_warning "Phase $phase: $result"
            ;;
    esac
done

log_info ""
log_info "Passed Phases: $PASSED_PHASES / $TOTAL_PHASES"
log_info "Validation completed at $(date)"
log_info "Full log saved to: $MASTER_LOG"

# Get dynamic version from wifit_core
WIFIT_VERSION=$(python3 -c "from wifit_core import __version__; print(__version__)" 2>/dev/null || echo "unknown")

# Generate JSON summary
SUMMARY_JSON="$LOGS_DIR/validation_summary_$TIMESTAMP.json"
cat > "$SUMMARY_JSON" << EOF
{
  "validation_run": {
    "timestamp": "$TIMESTAMP",
    "target_bssid": "$TEST_BSSID",
    "wifit_version": "$WIFIT_VERSION",
    "branch": "agent/wifit-v3"
  },
  "phases": {
EOF

for phase in {1..8}; do
    result="${PHASE_RESULTS[$phase]:-UNKNOWN}"
    echo "    \"phase_$phase\": \"$result\"" >> "$SUMMARY_JSON"
    if [[ $phase -lt 8 ]]; then
        echo "," >> "$SUMMARY_JSON"
    fi
done

cat >> "$SUMMARY_JSON" << EOF
  },
  "summary": {
    "total_phases": $TOTAL_PHASES,
    "passed": $PASSED_PHASES,
    "overall_status": "$([ $PASSED_PHASES -ge 6 ] && echo "PASS" || echo "FAIL")"
  }
}
EOF

log_info "Summary JSON saved to: $SUMMARY_JSON"

# Generate HTML Report
HTML_REPORT="$LOGS_DIR/validation_report_$TIMESTAMP.html"
if bash "$SCRIPT_DIR/generate_html_report.sh" \
    "$SUMMARY_JSON" "$MASTER_LOG" "$HTML_REPORT" 2>&1 | tee -a "$MASTER_LOG"; then
    if [[ ! -s "$HTML_REPORT" ]]; then
        log_error "HTML report generator returned success but produced an empty file"
        exit 1
    fi
    log_info "HTML report saved to: $HTML_REPORT"
else
    log_error "HTML report generation failed"
    exit 1
fi

# Final status - require ALL 8 phases for stable release
if [[ $PASSED_PHASES -eq 8 ]]; then
    log_success ""
    log_success "✓ VALIDATION PASSED"
    log_success "WiFiT is ready for stable release - all 8 phases passed"
    exit 0
else
    log_error ""
    log_error "✗ VALIDATION FAILED"
    log_error "Passed: $PASSED_PHASES/8 phases"
    log_error "All 8 phases must pass for stable release"
    exit 1
fi
