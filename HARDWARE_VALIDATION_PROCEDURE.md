# WiFiT v3.0.0-rc.1 Hardware Validation Procedure

**Version:** 1.0  
**Date:** 2026-08-05  
**Target Platform:** Rooted Android Device with Termux  
**Branch:** `agent/wifit-v3`  

---

## Prerequisites

### Required Hardware

1. **Android Device**
   - Rooted (Magisk or KernelSU)
   - Android 7.0+ recommended
   - Wireless chipset supporting monitor mode
   - Sufficient battery or external power

2. **Test Environment**
   - **Lab Test AP**: WPS-enabled test router
   - **Isolated Network**: No production traffic
   - **Physical Access**: Ability to reset AP if needed
   - **Documentation**: Record AP make/model/firmware

3. **Optional Equipment**
   - External USB wireless adapter (if internal chipset unsupported)
   - Secondary device for monitoring
   - Power bank for extended tests

### Software Requirements

```bash
# On Android/Termux
pkg update && pkg upgrade -y
pkg install root-repo -y
pkg install python git tsu iproute2 iw wpa-supplicant pixiewps -y

# Clone the branch
git clone -b agent/wifit-v3 https://github.com/TuHiN22/WiFiT.git
cd WiFiT

# Install WiFiT from this checkout with the minimal test dependency
python -m pip install -e '.[test]'
```

---

## Validation Procedure

Run the phase scripts from the normal Termux shell. Phases 1 and 2 request
one-shot root access through the command runner supplied by `tsu` when needed;
do not enter a persistent root shell first.

> **Current automated scope:** Phase scripts 1–3 are available in this release
> candidate. The master runner intentionally stops with an incomplete-suite
> diagnostic until phase scripts 4–8 are implemented. Run phases 1–3
> individually for this hardware re-test.

### Phase 1: Environment Setup (15 minutes)

#### Step 1.1: Verify Root Access

```bash
# Run validation script
bash validation/01_verify_environment.sh
```

Expected output:
```
✓ Root access confirmed
✓ Python 3.10+ detected
✓ Termux environment verified
✓ Required packages installed
```

#### Step 1.2: Identify Wireless Interface

```bash
# List interfaces
ip link show | grep wlan

# Or use iw
iw dev

# Record interface name (usually wlan0)
export WIFIT_INTERFACE=wlan0
```

#### Step 1.3: Test Interface Control

```bash
# Bring interface up
sudo ip link set $WIFIT_INTERFACE up

# Verify
ip link show $WIFIT_INTERFACE | grep UP
```

### Phase 2: Scanner Validation (20 minutes)

#### Step 2.1: Basic Scan Test

```bash
# Run automated scanner validation
bash validation/02_test_scanner.sh
```

This script will:
1. Scan for nearby networks
2. Verify WPS detection
3. Check WPS version parsing
4. Validate lock state detection
5. Extract WSC metadata
6. Identify WPA3 networks
7. Save results to `validation_logs/scanner_results.json`

#### Step 2.2: Manual Scan Verification

```bash
# Perform manual scan
sudo iw dev $WIFIT_INTERFACE scan | tee validation_logs/manual_scan.txt

# Compare with WiFiT scan
python3 -c "
from wifit_core.scanner import WiFiScanner
scanner = WiFiScanner('$WIFIT_INTERFACE')
aps = scanner.scan()
for ap in aps[:5]:
    print(f'{ap.bssid} {ap.ssid} WPS:{ap.wps} Ver:{ap.wps_version} Lock:{ap.wps_locked}')
" | tee -a validation_logs/wifit_scan.txt
```

### Phase 3: PIN Generation Validation (10 minutes)

#### Step 3.1: Test PIN Algorithms

```bash
# Run PIN generation validation
bash validation/03_test_pin_generation.sh <TEST_AP_BSSID>
```

This script will:
1. Generate all 39 registered PIN algorithms for target BSSID
2. Verify checksums
3. Show suggested PINs
4. Save to `validation_logs/pin_generation.json`

#### Step 3.2: Verify Against Known Defaults

```bash
# Check if any generated PINs match known defaults
python3 validation/check_default_pins.py <TEST_AP_BSSID>
```

### Phase 4: Process Management Validation (15 minutes)

#### Step 4.1: Test Process Discovery

```bash
# Run process management validation
bash validation/04_test_process_management.sh
```

This script will:
1. Discover interfering processes (wpa_supplicant, NetworkManager, etc.)
2. Stop discovered processes
3. Verify termination
4. Restore processes
5. Verify restoration
6. Check journal integrity
7. Save logs to `validation_logs/process_management.log`

#### Step 4.2: Test Cleanup After Interruption

```bash
# Start a managed process
sudo wpa_supplicant -i $WIFIT_INTERFACE &
WPA_PID=$!

# Simulate cleanup
python3 -c "
from wifit_core.process_manager import ProcessManager
pm = ProcessManager()
discovered = pm.discover()
print(f'Discovered {len(discovered)} processes')
pm.stop()
print('Processes stopped')
" | tee -a validation_logs/cleanup_test.log

# Verify restoration
ps aux | grep wpa_supplicant
```

### Phase 5: Live WPS Attack Validation (60 minutes)

#### Step 5.1: Automated Attack Test Suite

```bash
# Run comprehensive attack validation
sudo bash validation/05_test_wps_attacks.sh <TEST_AP_BSSID>
```

This script will test:
1. **Pixie Dust Attack** (if supported)
2. **PIN Bruteforce** (first 100 PINs only for validation)
3. **Algorithm-based PINs** (suggested for BSSID)
4. **Empty/Null PIN attempts**
5. **PBC (Push Button)** (if available)

Each test captures:
- Success/failure status
- Execution time
- Error messages
- wpa_supplicant debug output
- Recovery from failures

#### Step 5.2: Pixie Dust Validation (if AP vulnerable)

```bash
# Manual Pixie Dust test with full debugging
bash validation/pixie_dust_debug.sh <TEST_AP_BSSID>
```

Expected outcome:
- PKE, PKR, E-Hash1, E-Hash2, AuthKey, E-Nonce captured
- pixiewps invoked with correct parameters
- PIN recovered (if AP vulnerable)
- Logs saved to `validation_logs/pixie_dust_<BSSID>.log`

#### Step 5.3: Brute Force Validation (controlled test)

```bash
# Test first 50 PINs with session resume
bash validation/bruteforce_limited.sh <TEST_AP_BSSID> 50
```

This will:
1. Start brute force attack
2. Test first 50 PINs
3. Interrupt after PIN 25
4. Verify session saved
5. Resume from saved state
6. Complete remaining 25 PINs
7. Verify no duplicates
8. Save session data to `validation_logs/bruteforce_session.json`

### Phase 6: Reporter Validation (10 minutes)

#### Step 6.1: Test Export Formats

```bash
# Run reporter validation
bash validation/06_test_reporter.sh
```

This script will:
1. Create mock scan results
2. Create mock attack results (success and failure)
3. Export to TXT, CSV, JSON
4. Verify file permissions (0600 for files with credentials)
5. Verify CSV formula neutralization
6. Validate JSON schema
7. Save exports to `validation_logs/export_samples/`

### Phase 7: Stress Testing (120 minutes)

#### Step 7.1: Long-Duration Brute Force

```bash
# Run extended brute force (500 PINs)
sudo bash validation/07_stress_bruteforce.sh <TEST_AP_BSSID> 500
```

Monitor for:
- Memory leaks
- Process orphans
- Session corruption
- Rate limiting issues
- Network stack errors

#### Step 7.2: Scanner Stress Test

```bash
# Rapid repeated scans
bash validation/stress_scanner.sh 100
```

Performs 100 consecutive scans and checks for:
- Memory growth
- File descriptor leaks
- Interface state corruption
- Consistent parsing

### Phase 8: Recovery & Cleanup Validation (15 minutes)

#### Step 8.1: Test Graceful Shutdown

```bash
# Start attack and interrupt
bash validation/08_test_recovery.sh <TEST_AP_BSSID>
```

This script will:
1. Start WPS attack
2. Interrupt with Ctrl+C
3. Verify processes cleaned up
4. Verify interface restored
5. Verify sessions saved
6. Verify no orphans

#### Step 8.2: Test Crash Recovery

```bash
# Simulate crash and recovery
bash validation/crash_recovery.sh <TEST_AP_BSSID>
```

---

## Automated Validation Master Script

The master script orchestrates all validation phases:

```bash
# Run complete validation suite
sudo bash validation/run_all_validation.sh <TEST_AP_BSSID>
```

This will:
1. Run all phases sequentially
2. Capture all output to `validation_logs/master_run_<timestamp>.log`
3. Generate HTML report with pass/fail status
4. Create summary JSON with metrics
5. Package logs for analysis

Expected duration: **4-5 hours** for complete validation

---

## Log File Structure

All validation outputs are saved to:

```
WiFiT/
└── validation_logs/
    ├── master_run_<timestamp>.log          # Complete run log
    ├── environment_check.log               # Phase 1
    ├── scanner_results.json                # Phase 2
    ├── manual_scan.txt                     # Phase 2
    ├── wifit_scan.txt                      # Phase 2
    ├── pin_generation.json                 # Phase 3
    ├── process_management.log              # Phase 4
    ├── cleanup_test.log                    # Phase 4
    ├── attack_validation_<timestamp>.log   # Phase 5
    ├── pixie_dust_<BSSID>.log             # Phase 5.2
    ├── bruteforce_session.json            # Phase 5.3
    ├── export_samples/                     # Phase 6
    │   ├── test_scan.txt
    │   ├── test_scan.csv
    │   ├── test_scan.json
    │   ├── test_attacks.txt
    │   ├── test_attacks.csv
    │   └── test_attacks.json
    ├── stress_bruteforce_<timestamp>.log  # Phase 7
    ├── stress_scanner.log                  # Phase 7.2
    ├── recovery_test.log                   # Phase 8
    └── validation_report_<timestamp>.html  # Final report
```

---

## Success Criteria

### Phase 1: Environment ✅
- [ ] Root access confirmed
- [ ] Python 3.10+ available
- [ ] Required packages installed
- [ ] Wireless interface detected

### Phase 2: Scanner ✅
- [ ] Scans complete without errors
- [ ] WPS networks detected correctly
- [ ] WPS version parsed (1.0/2.0)
- [ ] Lock state detected (tri-state)
- [ ] WSC metadata extracted
- [ ] WPA3 detection works
- [ ] No crashes on malformed data

### Phase 3: PIN Generation ✅
- [ ] All 39 registered algorithms generate valid PINs
- [ ] Checksums correct for all PINs
- [ ] Vendor hints work correctly
- [ ] No duplicates in suggested list
- [ ] Empty PIN generates empty string

### Phase 4: Process Management ✅
- [ ] Interfering processes discovered
- [ ] Processes stopped cleanly
- [ ] Processes restored after stop
- [ ] Journal survives process restart
- [ ] No orphaned processes
- [ ] Idempotent restoration

### Phase 5: WPS Attacks ✅ (Critical)
- [ ] wpa_supplicant launches successfully
- [ ] WPS association succeeds
- [ ] Pixie Dust captures required data
- [ ] pixiewps invoked correctly
- [ ] PIN attempts reach AP
- [ ] Invalid PINs rejected by AP
- [ ] Valid PIN retrieves PSK
- [ ] Empty/null PIN attempts work
- [ ] PBC initiation works
- [ ] Session resume works correctly
- [ ] No infinite loops
- [ ] Cleanup after failures

### Phase 6: Reporter ✅
- [ ] TXT export contains all data
- [ ] CSV export valid format
- [ ] CSV formulas neutralized
- [ ] JSON export valid schema
- [ ] Credential files mode 0600
- [ ] Non-credential files mode 0644
- [ ] Atomic writes (no corruption)

### Phase 7: Stress Testing ✅
- [ ] No memory leaks over time
- [ ] No file descriptor leaks
- [ ] Session files don't grow unbounded
- [ ] 500+ PIN attempts stable
- [ ] 100+ scans stable
- [ ] No interface corruption

### Phase 8: Recovery ✅
- [ ] Ctrl+C cleanup works
- [ ] Processes restored after interrupt
- [ ] Sessions saved on interrupt
- [ ] Crash recovery works
- [ ] No orphans after kill -9

---

## Troubleshooting

### Common Issues

**Issue: "No wireless interface detected"**
```bash
# Check available interfaces
ip link show
iw list

# Verify wireless driver loaded
lsmod | grep -E 'wlan|wifi|80211'

# Check dmesg for errors
dmesg | tail -50
```

**Issue: "Root access denied"**
```bash
# Verify Magisk/KernelSU installed
su -c 'id'

# Check tsu installation
which tsu
pkg reinstall tsu
```

**Issue: "wpa_supplicant fails to start"**
```bash
# Check if already running
ps aux | grep wpa_supplicant

# Check interface state
ip link show $WIFIT_INTERFACE

# Try manual start
sudo wpa_supplicant -i $WIFIT_INTERFACE -c /tmp/test.conf -d
```

**Issue: "Pixie Dust data not captured"**
```bash
# Verify wpa_supplicant debug level
# Should see "WPS: Building Message M*" in output

# Check pixiewps installation
which pixiewps
pixiewps --help
```

**Issue: "Session resume fails"**
```bash
# Check session file
cat ~/.local/state/wifit/bruteforce-sessions/*.json

# Verify JSON validity
python3 -m json.tool <session_file>

# Check permissions
ls -la ~/.local/state/wifit/bruteforce-sessions/
```

---

## Reporting Issues

After validation, if issues found:

1. **Package Logs**
   ```bash
   cd WiFiT
   tar -czf validation_logs_$(date +%Y%m%d_%H%M%S).tar.gz validation_logs/
   ```

2. **Create Issue** on GitHub with:
   - Hardware details (device, chipset, Android version)
   - Test AP details (make, model, firmware)
   - Validation phase that failed
   - Attached log archive
   - Steps to reproduce

3. **Include Environment**
   ```bash
   bash validation/capture_environment.sh > environment_report.txt
   ```

---

## Post-Validation Steps

### If All Tests Pass ✅

1. **Tag Stable Release**
   ```bash
   git tag -a v3.0.0 -m "WiFiT v3.0.0 - Hardware validated"
   git push origin v3.0.0
   ```

2. **Update Documentation**
   - Mark RELEASE_NOTES as "Hardware Validated"
   - Add tested hardware list to README
   - Update badges

3. **Announce Release**
   - GitHub Releases page
   - Update README badges
   - Community announcement

### If Tests Fail ⚠️

1. **Document Failures** in validation_logs/
2. **Create Issues** for each failure
3. **Keep as RC** (do not tag stable)
4. **Fix Issues** and re-validate
5. **Tag next RC** (e.g., v3.0.0-rc.2)

---

## Safety Guidelines

### Before Starting

- ✅ Isolate test network
- ✅ Backup test AP configuration
- ✅ Have factory reset procedure ready

### During Testing

- ✅ Monitor for unintended disruption
- ✅ Stop if affecting other networks
- ✅ Document all activities
- ✅ Maintain physical control of test equipment

### After Testing

- ✅ Restore all configurations
- ✅ Verify no persistent changes
- ✅ Archive logs securely
- ✅ Document results

---

**Next:** Run phase scripts 1–3 individually. Do not use
`validation/run_all_validation.sh` until phase scripts 4–8 have been added.
