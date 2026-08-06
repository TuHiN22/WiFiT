# WiFiT v3.0.0-rc.3 Release Notes

**Release Date:** TBD  
**Release Type:** Pre-release (Release Candidate 3)  
**Previous Version:** v3.0.0-rc.2

---

## Overview

RC3 addresses all blocking issues identified in RC2 hardware validation. This release focuses on fixing API mismatches, improving attack reliability, enforcing quality gates, and fully integrating RC2 modules into the main application.

---

## Critical Fixes from RC2

### 1. **WPS Attack Controller Improvements**

**Issue:** wpa_supplicant controller was missing ATTACH command, preventing unsolicited event monitoring.

**Fix:**
- Added `ATTACH` command after control socket connection
- Now properly receives WPS transaction events (M-messages, credentials, failures)
- Fixed null PIN vs empty PIN distinction:
  - **Null PIN**: `WPS_REG <BSSID>` (no PIN parameter)
  - **Empty PIN**: `WPS_REG <BSSID> ""` (explicit empty string)
- Both methods now have separate code paths and attack methods

**Files:**
- `wifit_core/wps_attack.py`

### 2. **Pixiewps Success Detection**

**Issue:** pixiewps was treating any zero exit code as success, even without PIN recovery.

**Fix:**
- Success now requires BOTH:
  - Return code 0
  - Actual PIN extracted from output
- Prevents false positives from compatible-but-unsuccessful pixiewps runs

**Files:**
- `wifit_core/pixie_dust.py`

### 3. **Validation Script API Corrections**

**Issue:** Validation scripts called non-existent methods:
- `discover_interferers()` → use `discover()`
- `restore_stopped_processes()` → use `restore()`
- `_save_journal()` → don't call private methods
- `generate_pins()` → use `get_likely_pins()`
- `format_pin()` → use `wps_checksum()` directly
- `BruteforceSession.create()` → use `__init__()` + `.start()`
- Reporter methods → use `export()` with format parameter

**Fix:**
- Phase 4: Updated to use public `ProcessManager` API
- Phase 5: Fixed to use `get_likely_pins()`, removed legal warning banner, fixed zero PIN test
- Phase 6: Updated to use `ResultReporter.export()`
- Phase 8: Fixed to use proper session constructor

**Files:**
- `validation/04_test_process_management.sh`
- `validation/05_test_wps_attacks.sh`
- `validation/06_test_reporter.sh`
- `validation/08_test_recovery.sh`

### 4. **CI Quality Gate Enforcement**

**Issue:** All lint, security, and type-check jobs ended with `|| true`, making them non-blocking.

**Fix:**
- Removed `|| true` from all quality checks
- Ruff, mypy, and Bandit failures now block CI
- Forces code quality standards before merge

**Files:**
- `.github/workflows/ci.yml`

### 5. **Main Application Integration**

**Issue:** `wifit.py` still used legacy random PIN loop, none of the RC2 modules were integrated.

**Fix:**
- Replaced random PIN generation in `smart_bruteforce()` with:
  - Phase 1: Try algorithm-generated likely PINs via `get_likely_pins()`
  - Phase 2: Systematic split-half brute force via `BruteforceSession`
- Sessions are now resumable after interruption
- First-half validation properly tracked
- Progress automatically saved

**Files:**
- `wifit.py`

### 6. **PYTHONPATH Safety**

**Issue:** Validation scripts used unsafe `PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"` form.

**Fix:**
- All scripts now use: `PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"`
- Handles empty/unset PYTHONPATH gracefully (RC2 fix carried forward)

### 7. **Legal Warning Placement**

**Issue:** Phase 5 script displayed prominent legal warning in violation of project requirement.

**Fix:**
- Replaced red/alarming banner with yellow informational confirmation
- Legal warnings remain only in README.md and release notes

---

## Version Updates

All version strings updated from `3.0.0-rc.2` to `3.0.0-rc.3`:
- `wifit_core/__init__.py`
- `pyproject.toml`
- `wifit.py` (module docstring and banner)

---

## Test Status

### Unit Tests
- **Total:** 103 tests
- **Status:** All passing locally
- **Coverage:** 73.71% overall (requires improvement)

### Critical Coverage Gaps
- `wps_attack.py`: 24.90% (needs integration tests)
- Target: ≥85% overall, ≥90% for critical modules

### Validation Scripts
- Phase 1-3: Passing (environment, scanner, PIN generation)
- Phase 4: **Fixed** - Process management now uses correct APIs
- Phase 5: **Fixed** - WPS attack module imports and structure tests
- Phase 6: **Fixed** - Reporter uses correct export API
- Phase 7: Stress test (brute force performance)
- Phase 8: **Fixed** - Session recovery uses correct constructor

---

## Known Limitations

1. **Coverage Below Target**
   - Overall: 73.71% (target: ≥85%)
   - wps_attack.py: 24.90% (target: ≥90%)
   - Requires additional integration tests

2. **Ruff Errors**
   - 354 lint errors reported
   - Will now block CI (quality gate enforced)
   - Requires cleanup pass

3. **Hardware Validation Pending**
   - RC3 must be validated on actual hardware
   - All 8 phases must pass before stable release
   - Controlled test network required

---

## Migration from RC2

### Breaking Changes
None - RC3 is a pure bugfix release.

### API Changes
None - all changes are internal implementation fixes.

### For Developers
If you have custom validation scripts or integrations:
1. Update any calls to `discover_interferers()` → `discover()`
2. Update any calls to `restore_stopped_processes()` → `restore()`
3. Use `get_likely_pins(bssid)` instead of `generate_pins(bssid)`
4. Use `wps_checksum(pin_7digit)` directly for PIN formatting
5. Use `BruteforceSession(bssid)` constructor, then call `.start()`
6. Use `ResultReporter().export(path, attack_results=[...], report_format='txt')`

---

## Installation

### Fresh Install
```bash
cd ~/WiFiT
git fetch origin
git checkout agent/wifit-v3
git pull --ff-only origin agent/wifit-v3

# Install dependencies
pkg install root-repo -y
pkg install python git tsu iproute2 iw wpa-supplicant pixiewps -y

# Install WiFiT
python -m pip install -e '.[test]'

# Run tests
python -m pytest tests/ -v
```

### Upgrade from RC2
```bash
cd ~/WiFiT
git pull --ff-only origin agent/wifit-v3
python -m pip install -e '.[test]'
python -m pytest tests/ -v
```

---

## Hardware Validation Checklist

Before approving RC3 for stable release, verify:

- [ ] Phase 1: Environment validated (interface, root, dependencies)
- [ ] Phase 2: Scanner finds WPS-enabled test AP
- [ ] Phase 3: PIN generation produces expected algorithms
- [ ] Phase 4: Process management discovers/stops/restores interferers
- [ ] Phase 5: WPS attack modules import and structure correct
- [ ] Phase 6: Reporter exports all formats with correct permissions
- [ ] Phase 7: Brute force stress test completes
- [ ] Phase 8: Session recovery resumes correctly after interruption

---

## Next Steps for Stable v3.0.0

1. Complete hardware validation (all 8 phases)
2. Address coverage gaps (target ≥85% overall, ≥90% critical)
3. Fix Ruff lint errors (354 issues)
4. Add integration tests for wps_attack.py
5. Merge PR #2 into master
6. Tag v3.0.0 and publish as stable release

---

## Credits

- **Author:** TuHiN
- **Testing:** Android/Termux hardware validation
- **Framework:** Python 3.10+, pytest, wpa_supplicant, pixiewps

---

## License

MIT License - see LICENSE file for details.

---

## Disclaimer

WiFiT is intended for authorized security testing only. Users must:
- Own the target network OR
- Have explicit written permission

Unauthorized access to computer networks is illegal. WiFiT developers are not responsible for misuse.
