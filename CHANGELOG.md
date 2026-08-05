# Changelog

All notable changes to WiFiT will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0-rc.1] - 2026-08-05

### Added
- Complete PIN generation module with all 30 offline algorithms
- Deterministic, resumable split-half online WPS brute force
- True empty PIN, null PIN, explicit `00000000` PIN support
- Targeted PBC (Push Button Configuration) attack
- Validated Pixie Dust with PKE, PKR, hashes, AuthKey, nonces, BSSID
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
- Hardware validation on authorized targets pending
- Designed for rooted Android devices with Termux
- Functional parity with OneShot-Extended master commit 12d24a62
- For educational and authorized penetration testing purposes only

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

