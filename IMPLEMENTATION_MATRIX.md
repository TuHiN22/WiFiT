# WiFiT v3.0.0 Implementation & Compliance Matrix

**Generated:** 2026-08-05  
**Target:** OneShot-Extended master commit 12d24a62 functional parity  
**License:** GPL-2.0-or-later (changing from MIT per requirements)  

---

## Executive Summary

### Current State (v2.0.0)
- ✅ Interactive menu system with ANSI styling  
- ✅ Basic WPS attacks (Pixie Dust via `wpa_supplicant`, simple PIN attempts)  
- ✅ Core `wifit_core` modules: `runner`, `platform`, `scanner`, `reporter`, `models`, `vulnerability`, `process_manager`  
- ✅ Unit tests for core modules (platform, runner, scanner, reporter, vulnerability, process_manager)  
- ✅ Root elevation via `tsu`  
- ✅ TXT/CSV/JSON export  
- ⚠️  MIT License (must change to GPL-2.0-or-later)  
- ❌ No comprehensive WPS PIN algorithms (30 offline methods)  
- ❌ No split-half online brute force with resume  
- ❌ No `pixiewps` integration with validated parameters  
- ❌ No true empty/null PIN support  
- ❌ No explicit `00000000` PIN support  
- ❌ No targeted PBC (Push Button Configuration)  
- ❌ No comprehensive CLI coverage  
- ❌ No Python packaging (`setup.py`/`pyproject.toml`)  
- ❌ No changelog or v3.0.0 release notes  
- ❌ Missing required legal warning in banner/CLI/README  
- ❌ No coverage measurement infrastructure  
- ❌ No deterministic fake-tool test suite  

---

## Required Capabilities Matrix

| # | Capability | Status | Module | Tests | Notes |
|---|------------|--------|--------|-------|-------|
| 1 | PIN, null PIN, empty PIN, `00000000`, targeted PBC | ❌ TODO | `wps_attack.py` | ❌ | Needs `wpa_supplicant` integration |
| 2 | Pixie Dust with validated PKE/PKR/hashes/AuthKey/nonces/BSSID/modes/timeout/force | ⚠️ PARTIAL | Extend `wifit.py` | ❌ | Basic structure exists, needs validation |
| 3 | Deterministic resumable split-half online brute force | ❌ TODO | `wps_bruteforce.py` | ❌ | Must avoid recursion, atomic resume |
| 4 | All 30 offline PIN algorithms | ⚠️ PARTIAL | `wifit.py` has 26 | ⚠️ | Need complete `pin_generator.py` |
| 5 | Robust `iw` scanning with recovery, WPS version/lock/WSC/WPA3 | ✅ DONE | `scanner.py` | ✅ | Excellent implementation |
| 6 | TXT, CSV, JSON export with atomic writes and mode 0600 for credentials | ✅ DONE | `reporter.py` | ✅ | Formula neutralization included |
| 7 | Unified Linux/Android process/radio/settings lifecycle with restoration | ✅ DONE | `platform.py`, `process_manager.py` | ✅ | Excellent implementation |
| 8 | Comprehensive CLI coverage + interactive menu | ⚠️ PARTIAL | `cli.py` + `wifit.py` | ❌ | Menu exists, CLI needs expansion |
| 9 | Python packaging (`pyproject.toml`, `setup.py`) | ❌ TODO | Project root | ❌ | Required for distribution |
| 10 | GPL-2.0-or-later licensing, attribution, changelog | ❌ TODO | `LICENSE`, `CHANGELOG.md` | N/A | Currently MIT |
| 11 | Required legal warning in all user-facing surfaces | ❌ TODO | README, CLI, banner | N/A | Exact text specified |
| 12 | Termux installer with syntax checks | ⚠️ PARTIAL | `install.sh` | ❌ | Exists but needs GPL update |

---

## Security & Quality Gates

| Gate | Requirement | Status | Action |
|------|-------------|--------|--------|
| **No `shell=True`** | Zero operational command strings | ✅ PASS | `runner.py` enforces argv lists |
| **Input validation** | Interface/BSSID regex validated | ✅ PASS | `models.py` normalizes BSSIDs |
| **Bounded operations** | Every subprocess/socket/retry has finite deadline | ✅ PASS | `runner.py` mandatory timeout |
| **Process termination** | Conservative, identity-verified, journaled, idempotent | ✅ PASS | `process_manager.py` excellent |
| **CSV formula neutralization** | Dangerous prefixes escaped | ✅ PASS | `reporter.py` implements |
| **Credential file permissions** | mode 0600 for files with PIN/PSK | ✅ PASS | `reporter.py` detects and applies |
| **Coverage ≥85% overall** | Measured with `pytest --cov` | ❌ TODO | Need `pytest`, `pytest-cov` setup |
| **Coverage ≥90% critical** | Scanner, PIN algorithms, WPS lifecycle, process mgmt, exporters | ❌ TODO | Need deterministic fake-tool tests |
| **Brute force correctness** | Exact `0000..9999` + `000..999` coverage, checksum, atomic resume | ❌ TODO | New module required |
| **Scanner robustness** | 10,000-BSS synthetic scan linear/memory-bounded, no crash on fuzz | ✅ LIKELY | `scanner.py` parse only, test needed |
| **No orphan processes** | All descendants cleaned up | ✅ PASS | `runner.py` uses process groups |
| **Type checking** | `mypy --strict` or equivalent | ❌ TODO | Code uses type hints, need CI check |
| **Linting** | Ruff or equivalent | ❌ TODO | Need configuration |
| **Compileall** | `python -m compileall` passes | ⚠️ UNTESTED | Likely passes, need CI check |
| **Bandit security scan** | No high-severity findings | ❌ TODO | Need scan |
| **Build verification** | Install from sdist in clean venv | ❌ TODO | Need packaging first |
| **`git diff --check`** | No trailing whitespace | ❌ TODO | Pre-commit hook recommended |
| **Installer syntax** | `bash -n install.sh` + shellcheck | ⚠️ UNTESTED | Likely passes |

---

## Test Coverage Plan

### Existing Tests (✅)
- `tests/test_runner.py` - Command runner with timeouts, arg boundaries
- `tests/test_scanner.py` - iw parse, WPS version, retry/recovery
- `tests/test_reporter.py` - TXT/CSV/JSON export, permissions
- `tests/test_platform.py` - Interface selection, rfkill, Android settings
- `tests/test_vulnerability.py` - WSC fingerprint matching
- `tests/test_process_manager.py` - Process discovery, stop, restore, journal

### Required New Tests (❌)
- `tests/test_pin_generator.py` - All 30 algorithms, checksum, MAC variants
- `tests/test_wps_bruteforce.py` - Split-half coverage, resume, no recursion
- `tests/test_wps_attack.py` - PIN/null/empty/zero/PBC with fake `wpa_supplicant`
- `tests/test_pixie_dust.py` - Parameter validation, `pixiewps` invocation (fake)
- `tests/test_cli.py` - Argument parsing, help text, validation
- `tests/test_integration.py` - End-to-end with fake tools
- `tests/test_scanner_stress.py` - 10,000-BSS synthetic scan
- `tests/test_scanner_fuzz.py` - Malformed iw output resilience

### Coverage Measurement
```bash
pip install pytest pytest-cov
pytest --cov=wifit_core --cov=wifit --cov-report=term-missing --cov-report=html
```

**Target:** ≥85% overall, ≥90% for critical modules (scanner, PIN gen, WPS lifecycle, process mgmt, reporters)

---

## File Structure (Target v3.0.0)

```
WiFiT/
├── wifit.py                    # Main entry point (legacy monolith to refactor)
├── wifit_core/
│   ├── __init__.py
│   ├── models.py               ✅ DONE
│   ├── runner.py               ✅ DONE
│   ├── platform.py             ✅ DONE
│   ├── process_manager.py      ✅ DONE
│   ├── scanner.py              ✅ DONE
│   ├── vulnerability.py        ✅ DONE
│   ├── reporter.py             ✅ DONE
│   ├── pin_generator.py        ❌ TODO (30 algorithms)
│   ├── wps_bruteforce.py       ❌ TODO (split-half with resume)
│   ├── wps_attack.py           ❌ TODO (PIN/null/empty/zero/PBC)
│   ├── pixie_dust.py           ❌ TODO (validated pixiewps invocation)
│   ├── cli.py                  ❌ TODO (argparse interface)
│   ├── menu.py                 ⚠️ EXTRACT from wifit.py
│   └── data/
│       └── vulnerable_wsc.txt  ✅ EXISTS
├── tests/
│   ├── test_*.py               ⚠️ 7 exist, 8 needed
│   └── fixtures/               ❌ TODO (fake tool outputs)
├── install.sh                  ⚠️ UPDATE for GPL
├── LICENSE                     ❌ CHANGE to GPL-2.0-or-later
├── README.md                   ⚠️ UPDATE with required warning
├── CHANGELOG.md                ❌ CREATE
├── CONTRIBUTING.md             ❌ CREATE (attribution requirements)
├── pyproject.toml              ❌ CREATE
├── setup.py                    ❌ CREATE (or use pyproject.toml only)
├── requirements.txt            ❌ CREATE (or use pyproject.toml)
├── requirements-dev.txt        ❌ CREATE
└── .github/workflows/ci.yml    ❌ OPTIONAL (quality gates)
```

---

## Implementation Plan (Phased)

### Phase 1: Foundation & Licensing (CRITICAL)
1. ✅ Change LICENSE from MIT to GPL-2.0-or-later
2. ✅ Add required legal warning to README, CLI help, banner
3. ✅ Create CHANGELOG.md with v3.0.0-rc.1 entry
4. ✅ Create CONTRIBUTING.md with attribution requirements
5. ✅ Add GPL headers to all Python source files
6. ✅ Update install.sh license references

### Phase 2: PIN Generation & Algorithms
1. ✅ Extract and complete `pin_generator.py` with all 30 algorithms
2. ✅ Add `test_pin_generator.py` with full coverage
3. ✅ Verify checksum algorithm matches WPS spec

### Phase 3: WPS Attack Infrastructure
1. ✅ Create `wps_attack.py` with PIN/null/empty/zero/PBC support
2. ✅ Create `pixie_dust.py` with validated parameter handling
3. ✅ Create `wps_bruteforce.py` with deterministic split-half and resume
4. ✅ Add corresponding test files with fake `wpa_supplicant`/`pixiewps`

### Phase 4: CLI & Menu Integration
1. ✅ Create `cli.py` with comprehensive `argparse` interface
2. ✅ Extract menu system from `wifit.py` to `menu.py`
3. ✅ Integrate CLI + menu with new attack modules
4. ✅ Add `test_cli.py`

### Phase 5: Packaging & Distribution
1. ✅ Create `pyproject.toml` or `setup.py` (PEP 517/518)
2. ✅ Create `requirements.txt` and `requirements-dev.txt`
3. ✅ Test sdist/wheel build
4. ✅ Test clean venv install

### Phase 6: Quality Gates & Testing
1. ✅ Add `pytest`, `pytest-cov` to dev requirements
2. ✅ Run coverage measurement, fix gaps to ≥85%/≥90%
3. ✅ Add stress tests (10K-BSS scan, fuzz inputs)
4. ✅ Run `mypy --strict`, `ruff`, `bandit`, `compileall`
5. ✅ Run `bash -n install.sh` and shellcheck
6. ✅ Fix all findings

### Phase 7: Git Workflow & Release
1. ✅ Audit `git status` and `.gitignore`
2. ✅ Create branch `agent/wifit-v3`
3. ✅ Commit scoped changes (no unrelated files)
4. ✅ Push branch
5. ✅ Open draft PR
6. ✅ Tag `v3.0.0-rc.1` (prerelease without hardware validation)
7. ⏸️ Hardware validation (user-provided authorized lab target)
8. ⏸️ Tag `v3.0.0` stable (only after hardware checklist)

---

## Known Limitations & Risks

1. **Hardware validation unavailable in this environment** → RC/prerelease only
2. **Upstream OneShot-Extended uses unsafe patterns** → We improve, not copy
3. **`wpa_supplicant` output parsing is fragile** → Needs extensive fake-tool tests
4. **WPS lock detection unreliable** → Scanner reports tri-state (True/False/None)
5. **Android/Termux environment diversity** → Test on multiple Android versions if possible
6. **RF transmission requires root + wireless hardware** → Unit tests use fakes
7. **External tool dependencies** (`iw`, `pixiewps`, `wpa_supplicant`) → Graceful degradation if missing

---

## Attribution & Upstream

WiFiT v3.0.0 is a refactored and expanded fork of prior work by TuHiN (v2.0.0) which itself combined concepts from:
- W8RootWifiHKV2 (menu system, UI design)
- FARHAN-Shot (architecture)
- OneShotPin (PIN algorithms) 
- Pixiewps (Pixie Dust implementation)

Functional requirements target OneShot-Extended master commit 12d24a62, but implementation improves upon upstream defects (no `shell=True`, bounded operations, testable boundaries).

---

## Compliance Checklist (Pre-Release)

- [ ] LICENSE is GPL-2.0-or-later
- [ ] Required warning in README, CLI help, startup banner, release notes
- [ ] All 12 required capabilities implemented
- [ ] All security gates pass
- [ ] Coverage ≥85% overall, ≥90% critical
- [ ] Brute force: exact 0000-9999 + 000-999 coverage, correct checksum, atomic resume, no recursion
- [ ] Scanner: 10K-BSS linear/memory-bounded, no fuzz crash
- [ ] No orphan processes
- [ ] Type checking passes
- [ ] Ruff passes
- [ ] Bandit passes (no high-severity)
- [ ] Compileall passes
- [ ] Build verification (clean venv install from sdist)
- [ ] `git diff --check` clean
- [ ] Installer syntax check passes
- [ ] Python 3.10-3.14 tested
- [ ] Zero arguments opens menu
- [ ] Legacy CLI flags supported
- [ ] Changelog complete
- [ ] CONTRIBUTING.md exists
- [ ] No unsupported claims (AI, timeout, hardware without validation)
- [ ] Commit only scoped files to `agent/wifit-v3`
- [ ] Draft PR opened
- [ ] Tag `v3.0.0-rc.1` as prerelease (no hardware validation)

---

**Status:** MATRIX ESTABLISHED  
**Next:** Begin Phase 1 (Foundation & Licensing)
