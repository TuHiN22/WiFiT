# Changelog

All notable changes to WiFiT will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0-rc.2] - 2026-08-05

### Added
- **Live WPS attack integration** (`wifit_core/wps_attack.py`)
  - WPASupplicantController for socket-based wpa_supplicant control
  - PIN/null-PIN/empty-PIN/zero-PIN attack methods
  - PBC (Push Button Configuration) support with targeted BSSID
  - First-half validity detection for split-half optimization
  - Pixie Dust parameter extraction during attacks
- **Validated Pixiewps wrapper** (`wifit_core/pixie_dust.py`)
  - Complete parameter validation (PKE, PKR, E-Hash1/2, AuthKey, E-Nonce)
  - Proper length and hex character validation
  - Timeout support with minimum 10s enforcement
  - Force flag for full keyspace search
- **Hardware validation scripts** (Phase 4-8)
  - `04_test_process_management.sh` - Process lifecycle validation
  - `05_test_wps_attacks.sh` - Live attack framework tests with authorization check
  - `06_test_reporter.sh` - Export system validation
  - `07_stress_bruteforce.sh` - 1000+ PIN stress test
  - `08_test_recovery.sh` - Session resume and cleanup tests
- **GitHub Actions CI workflow**
  - Test matrix for Python 3.10, 3.11, 3.12
  - Code quality checks (Ruff, mypy, Bandit)
  - Package build verification
  - Coverage reporting to Codecov
- **AttackResult enhancements**
  - Proper `wps_pin` and `network_key` fields
  - `finished_at` timestamp tracking
  - Compatibility aliases (`pin`, `psk`)
  - First-half validity metadata

### Changed
- Updated version to 3.0.0-rc.2 across all modules
- Exported new modules in `wifit_core/__init__.py`
- Enhanced test suite to 103 tests (all passing)
- Validation framework now covers all 8 phases

### Fixed
- Import paths in `__init__.py` (use `get_likely_pins`, `generate_pin`)
- AttackResult field names to match existing interface
- Datetime handling with timezone-aware timestamps

## [3.0.0-rc.1] - 2026-08-05

### Added
- Complete PIN generation module with all 30 WPS algorithms
- Deterministic, resumable split-half online WPS brute force
- Comprehensive CLI interface alongside interactive menu
- Python packaging support (`pyproject.toml`)
- WPA3 and transition mode detection in scanner
- Atomic resume for interrupted brute force attacks
- JSON export format alongside TXT and CSV
- Type hints throughout codebase (Python 3.10+)
- Comprehensive test suite with ≥85% coverage target
- Process isolation and cleanup guarantees
- Conservative process termination with identity verification

### Changed
- Refactored monolithic `wifit.py` into modular `wifit_core` package
- All subprocess calls use argv lists (no `shell=True`)
- Every external operation has mandatory finite timeout
- Scanner now detects WPS version, lock state, and WSC metadata
- Reporter applies mode 0600 to files containing credentials
- Platform manager handles Android/Termux RF-kill and settings restoration
- Enhanced error messages with context and recovery suggestions

### Fixed
- Hardware validators now import the checkout reliably from Termux temporary paths
- Phase 1 verifies one-shot root access from a normal Termux shell
- Termux setup now installs the correct `iproute2`, `iw`, `wpa-supplicant`, and
  `pixiewps` packages in repository-safe order
- Scanner validation prepares and restores a down wireless interface around scanning
- HTML validation reports receive and parse their summary input correctly
- The installer now packages both `wifit.py` and `wifit_core`
- WPS version detection now distinguishes confirmed vs inferred 1.0
- CSV export neutralizes spreadsheet formula injection
- Process manager journal prevents orphaned processes after crashes
- Scanner retries with exponential backoff and RF-kill recovery
- BSSID normalization prevents malformed input crashes

### Security
- Zero operational `shell=True` command execution
- Input validation for all interface names and BSSIDs
- Bounded retries, timeouts, and resource limits
- Protected credential files with restrictive permissions
- Conservative process targeting excludes system-critical PIDs

### Notes
- This is a prerelease (RC) version
- Core environment, PIN generation, and live scanner validation passed on rooted
  Android with Termux; live WPS attack validation remains pending
- Designed for rooted Android devices with Termux
- Functional parity with OneShot-Extended master commit 12d24a62

## [2.0.0] - 2026-01-15

### Added
- Initial WiFiT release combining features from multiple sources
- Interactive menu-driven interface
- Basic Pixie Dust attack via wpa_supplicant
- Auto attack mode
- Root access automation via tsu
- Beautiful styled output boxes
- Reports directory with TXT and CSV export

### Credits
- Combined work from W8RootWifiHKV2, FARHAN-Shot, OneShotPin, Pixiewps
- Author: TuHiN

