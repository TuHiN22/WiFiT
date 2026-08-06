#!/bin/bash
#
# WiFiT Master Hardware Validation Script
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
    local wifit_version=$(python3 -c "from wifit_core import __version__; print(__version__)" 2>/dev/null || echo "unknown")
    cat << EOF | tee -a "$MASTER_LOG"
╔══════════════════════════════════════════════════════════════╗
║        WiFiT $wifit_version Hardware Validation Suite       ║
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

# Validate and normalize BSSID once upfront
validate_bssid() {
    local bssid="$1"
    # Validate format: XX:XX:XX:XX:XX:XX where X is hex
    if [[ ! "$bssid" =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]]; then
        log_error "Invalid BSSID format: $bssid"
        log_error "Expected format: AA:BB:CC:DD:EE:FF (hex octets separated by colons)"
        exit 1
    fi
    # Normalize to uppercase
    echo "$bssid" | tr '[:lower:]' '[:upper:]'
}

TEST_BSSID=$(validate_bssid "$TEST_BSSID")
log_info "Normalized BSSID: $TEST_BSSID"

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

# Collect provenance at END (after Phase 8) to detect any changes
collect_git_provenance "end"

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

# ============================================================================
# Git Provenance Collection - START
# ============================================================================
# Use command-scoped safe.directory (read-only, no repository mutation)
# Capture provenance at start AND end to detect any changes during validation

collect_git_provenance() {
    local phase="$1"  # "start" or "end"

    # Full 40-character commit SHA (command-scoped safe.directory)
    if ! GIT_COMMIT_FULL=$(git -c "safe.directory=$REPO_ROOT" -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null); then
        log_error "BLOCKER: Cannot determine commit SHA at validation $phase."
        log_error "Git provenance is mandatory. This validation cannot be tied to a reproducible commit."
        exit 2
    fi

    # Short SHA for display
    GIT_COMMIT_SHORT=$(git -c "safe.directory=$REPO_ROOT" -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo "unknown")

    # Branch or detached HEAD
    GIT_BRANCH=$(git -c "safe.directory=$REPO_ROOT" -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    if [[ "$GIT_BRANCH" == "HEAD" ]]; then
        GIT_BRANCH="detached"
    fi

    # Exact tag if present
    GIT_TAG=$(git -c "safe.directory=$REPO_ROOT" -C "$REPO_ROOT" describe --tags --exact-match 2>/dev/null || echo "")

    # Complete dirty status (working tree + index + untracked)
    GIT_STATUS_PORCELAIN=$(git -c "safe.directory=$REPO_ROOT" -C "$REPO_ROOT" status --porcelain 2>/dev/null || echo "")
    if [[ -z "$GIT_STATUS_PORCELAIN" ]]; then
        GIT_CLEAN="true"
        GIT_DIRTY=""
    else
        GIT_CLEAN="false"
        GIT_DIRTY="-dirty"
    fi

    # Export for comparison between start/end
    if [[ "$phase" == "start" ]]; then
        export GIT_COMMIT_FULL_START="$GIT_COMMIT_FULL"
        export GIT_CLEAN_START="$GIT_CLEAN"
        export GIT_STATUS_START="$GIT_STATUS_PORCELAIN"

        log_info "Git Provenance (validation start):"
        log_info "  Commit (full): $GIT_COMMIT_FULL"
        log_info "  Commit (short): $GIT_COMMIT_SHORT"
        log_info "  Branch: $GIT_BRANCH"
        log_info "  Tag: ${GIT_TAG:-none}"
        log_info "  Clean: $GIT_CLEAN"

        # Fail immediately if worktree is dirty at start
        if [[ "$GIT_CLEAN" != "true" ]]; then
            log_error "BLOCKER: Worktree is dirty at validation start."
            log_error "Validation requires a clean checkout of an exact commit/tag."
            log_error "Dirty files:"
            echo "$GIT_STATUS_PORCELAIN" | tee -a "$MASTER_LOG"
            exit 2
        fi
    else
        # Verify provenance hasn't changed during validation
        if [[ "$GIT_COMMIT_FULL" != "$GIT_COMMIT_FULL_START" ]]; then
            log_error "BLOCKER: Git commit SHA changed during validation!"
            log_error "  Start: $GIT_COMMIT_FULL_START"
            log_error "  End:   $GIT_COMMIT_FULL"
            log_error "Validation results are invalid - tested commit is unknown."
            exit 2
        fi

        if [[ "$GIT_CLEAN" != "$GIT_CLEAN_START" ]]; then
            log_error "BLOCKER: Worktree state changed during validation!"
            log_error "  Start: clean=$GIT_CLEAN_START"
            log_error "  End:   clean=$GIT_CLEAN"
            if [[ "$GIT_CLEAN" == "false" ]]; then
                log_error "Dirty files at end:"
                echo "$GIT_STATUS_PORCELAIN" | tee -a "$MASTER_LOG"
            fi
            log_error "Validation results are invalid - tested code is uncertain."
            exit 2
        fi

        log_info "Git Provenance (validation end):"
        log_info "  Commit: $GIT_COMMIT_FULL (unchanged ✓)"
        log_info "  Worktree: clean (unchanged ✓)"
    fi
}

# Get dynamic version
WIFIT_VERSION=$(python3 -c "from wifit_core import __version__; print(__version__)" 2>/dev/null || echo "unknown")

# Collect provenance at START (before Phase 1)
collect_git_provenance "start"

# Compute overall status (must pass ALL 8 phases)
if [[ $PASSED_PHASES -eq $TOTAL_PHASES ]]; then
    OVERALL_STATUS="PASS"
else
    OVERALL_STATUS="FAIL"
fi

# Generate JSON summary using Python with safe argument passing
SUMMARY_JSON="$LOGS_DIR/validation_summary_$TIMESTAMP.json"

# Build phase results as a JSON object
PHASES_JSON="{"
for phase in {1..8}; do
    result="${PHASE_RESULTS[$phase]:-UNKNOWN}"
    PHASES_JSON+="\"phase_$phase\": \"$result\""
    if [[ $phase -lt 8 ]]; then
        PHASES_JSON+=","
    fi
done
PHASES_JSON+="}"

# Pass data as environment variables to avoid injection
export JSON_TIMESTAMP="$TIMESTAMP"
export JSON_TARGET_BSSID="$TEST_BSSID"
export JSON_WIFIT_VERSION="$WIFIT_VERSION"
export JSON_GIT_COMMIT_FULL="$GIT_COMMIT_FULL"
export JSON_GIT_COMMIT_SHORT="$GIT_COMMIT_SHORT"
export JSON_GIT_BRANCH="$GIT_BRANCH"
export JSON_GIT_TAG="$GIT_TAG"
export JSON_GIT_CLEAN="$GIT_CLEAN"
export JSON_GIT_STATUS_PORCELAIN="$GIT_STATUS_PORCELAIN"
export JSON_PHASES="$PHASES_JSON"
export JSON_TOTAL_PHASES="$TOTAL_PHASES"
export JSON_PASSED_PHASES="$PASSED_PHASES"
export JSON_OVERALL_STATUS="$OVERALL_STATUS"

python3 << 'PYEOF' > "$SUMMARY_JSON"
import json
import os
import sys

# Read from environment variables (safe from injection)
data = {
    "validation_run": {
        "timestamp": os.environ.get("JSON_TIMESTAMP", ""),
        "target_bssid": os.environ.get("JSON_TARGET_BSSID", ""),
        "wifit_version": os.environ.get("JSON_WIFIT_VERSION", "")
    },
    "git_provenance": {
        "commit_full": os.environ.get("JSON_GIT_COMMIT_FULL", ""),
        "commit_short": os.environ.get("JSON_GIT_COMMIT_SHORT", ""),
        "branch": os.environ.get("JSON_GIT_BRANCH", ""),
        "tag": os.environ.get("JSON_GIT_TAG", ""),
        "clean": os.environ.get("JSON_GIT_CLEAN", "") == "true",
        "status_porcelain": os.environ.get("JSON_GIT_STATUS_PORCELAIN", "")
    },
    "phases": json.loads(os.environ.get("JSON_PHASES", "{}")),
    "summary": {
        "total_phases": int(os.environ.get("JSON_TOTAL_PHASES", "0")),
        "passed": int(os.environ.get("JSON_PASSED_PHASES", "0")),
        "overall_status": os.environ.get("JSON_OVERALL_STATUS", "")
    }
}

try:
    print(json.dumps(data, indent=2))
except Exception as e:
    sys.stderr.write(f"JSON generation failed: {e}\n")
    sys.exit(1)
PYEOF

if [[ ! -s "$SUMMARY_JSON" ]]; then
    log_error "JSON generation produced empty file"
    exit 1
fi

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

# Final status - use computed OVERALL_STATUS
if [[ "$OVERALL_STATUS" == "PASS" ]]; then
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
