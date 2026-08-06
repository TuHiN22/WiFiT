# WiFiT - Professional WPS Testing Toolkit

<div align="center">

```
╔══════════════════════════════════════════════════════════════╗
║                   🛡️  WiFiT v3.0.0-rc.9                     ║
║         Professional WPS Testing Toolkit for Termux          ║
║                      Author: TuHiN                           ║
╚══════════════════════════════════════════════════════════════╝
```

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Rooted%20Android%20%2B%20Termux-brightgreen.svg)](https://github.com/TuHiN22/WiFiT)
[![Root Required](https://img.shields.io/badge/root-required-red.svg)](https://magisk.me/)
[![Version](https://img.shields.io/badge/version-3.0.0--rc.9-orange.svg)](#changelog)

**🔥 Designed exclusively for Rooted Android Devices with Termux**

**A powerful hybrid WiFi penetration testing tool combining advanced WPS attack methods**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Validation](#-validation-procedure) • [Legal](#%EF%B8%8F-legal-disclaimer)

</div>

---

## 🎯 About

WiFiT is a professional WPS (Wi-Fi Protected Setup) penetration testing toolkit **specifically designed for Rooted Android devices running Termux**. It combines the best features from multiple WiFi security testing tools with an intuitive menu-driven interface, multiple attack modes, and automated network discovery.

### 📱 Platform Requirements

**Designed For:**
- ✅ Rooted Android Devices (Magisk / KernelSU)
- ✅ Termux Terminal Emulator
- ✅ Android 7.0+ recommended

### 🌟 Key Highlights

- **🚀 Auto Attack Mode** - Automatically scan and attack all WPS-enabled networks
- **⚡ Pixie Dust Attack** - Fast WPS PIN recovery using known vulnerabilities
- **💪 Brute Force Mode** - Systematic PIN testing with smart algorithms
- **🤖 Smart Attack** - AI-enhanced PIN prediction and recovery
- **� Root Fix Tool** - Built-in superuser access repair utility
- **�📊 Beautiful Results** - Styled output boxes with color-coded information
- **📋 Comprehensive Logging** - All results saved with timestamps
- **🎨 Modern UI** - Color-coded Termux-optimized interface

---

## ✨ Features

### Attack Modes

1. **Auto Attack**
   - Scans all nearby WPS networks
   - Automatically attempts Pixie Dust on each target
   - 30-second timeout per target
   - Detailed attack summary

2. **Pixie Dust Attack**
   - Exploits weak random number generators
   - Fast PIN recovery (seconds to minutes)
   - Highest success rate on vulnerable routers

3. **Brute Force Attack**
   - Smart PIN generation based on MAC address
   - Vendor-specific PIN algorithms
   - Progress tracking with ETA

4. **Smart Attack**
   - Combines Pixie Dust and Brute Force
   - Automatic fallback on failure
   - Optimized attack sequence

5. **Root Fix Tool** 🆕
   - Automatically diagnose root issues
   - Remove conflicting packages
   - Install required root tools
   - Scan for su binaries (Magisk/KernelSU)
   - Test root access

### Additional Features

- **Network Scanner** - Displays WPS-enabled networks with signal strength
- **Password Manager** - View all cracked credentials
- **Beautiful Result Display** - Styled boxes with color-coded output
- **Multiple Export Formats** - TXT and CSV output
- **Session Management** - Resume interrupted attacks
- **MAC Address Support** - Vendor-specific algorithms for major brands
- **No sudo Required** - Automatic root elevation in Termux

---

## 📋 Requirements

### System Requirements

- **Device**: Rooted Android device
- **Root Method**: Magisk or KernelSU
- **Termux**: Latest version from F-Droid
- **Python**: 3.10 or higher
- **Root Access**: Required for WiFi operations

### Root Setup

1. **Install Root Manager**
   - [Magisk](https://github.com/topjohnwu/Magisk) (Recommended)
   - [KernelSU](https://kernelsu.org/) (Alternative)

2. **Approve Termux When WiFiT Requests Root**
   - Start WiFiT normally with `wifit`
   - Approve the Magisk/KernelSU popup
   - No manual `tsu` shell is required

### Dependencies

**Termux Packages:**
- `python` - Python interpreter (`python`/`python3` commands)
- `tsu` - Termux superuser utility
- `root-repo` - Root-related packages
- `iproute2` - Interface state and link management (`ip`)
- `iw` - Modern wireless interface and scan control
- `wpa-supplicant` - WPS enrollee and control interface
- `pixiewps` - Pixie Dust PIN recovery engine

**Python Packages (Optional):**
- `pyfiglet` - ASCII art banners
- `psutil` - System information

---

## 🚀 Installation

### Quick Install (One Command) ⚡

```bash
curl -sL https://raw.githubusercontent.com/TuHiN22/WiFiT/master/install.sh | bash
```

### Termux Installation (Step by Step)

```bash
# 1. Install Termux from F-Droid (NOT Play Store!)
# Download: https://f-droid.org/packages/com.termux/

# 2. Update Termux packages
pkg update && pkg upgrade -y

# 3. Clone WiFiT repository
pkg install git -y
git clone https://github.com/TuHiN22/WiFiT.git
cd WiFiT

# 4. Run installer
bash install.sh

# 5. Start WiFiT and grant root permission when prompted
wifit
```

### First Time Setup

```bash
# WiFiT elevates automatically through the command runner supplied by tsu:

# 1. Start WiFiT
wifit

# 2. Grant permission in the Magisk/KernelSU popup
# (Check "Remember choice" for convenience)
```

---

## 📖 Usage

### Basic Usage

```bash
# Simply run (no sudo needed!)
wifit
```

### Menu Options

```
╔══════════════════════════════════════════════════════════════╗
║                      🎯 WiFiT Main Menu                     ║
╠══════════════════════════════════════════════════════════════╣
║  [1] 🚀 Auto Attack - Scan & Attack All WPS Networks        ║
║  [2] 🎯 Pixie Dust Attack - Fast WPS PIN Recovery           ║
║  [3] 💪 Brute Force Attack - Systematic PIN Testing         ║
║  [4] 🤖 Smart PIN Attack - AI-Enhanced Recovery             ║
║  [5] 📋 View Saved Passwords                                ║
║  [6] 🔧 Fix Root Issues - Repair Superuser Access           ║
║  [7] 🚪 Exit                                                ║
╚══════════════════════════════════════════════════════════════╝
```

### Result Display

When an attack is successful, you'll see a beautiful result box:

```
┌─[ WiFiT ]───[ CRACKED ]──────────────────────────────────┐
│                                                            │
│ PIN  : 12345678                                           │
│ PSK  : MyHomePa$$word!                                    │
│ SSID : TP-Link_HOME                                       │
│                                                            │
└─[ Stay With TuHiN ]──────────────────────────────────────┘

[+] Saved → reports/WiFiT_saved_data.txt

[i] Credentials saved to reports/WiFiT_Results.txt, reports/stored.csv
```

### Step-by-Step Guide

1. **Launch WiFiT**
   ```bash
   wifit
   ```

2. **Select Attack Mode**
   - Choose option 1-4 based on your needs
   - Option 1 (Auto Attack) is recommended for beginners

3. **Scan Networks**
   - WiFiT will scan for WPS-enabled networks
   - Networks are sorted by signal strength
   - If no networks found, press Enter to retry or 'q' to quit

4. **Select Target**
   - Enter the number of target network
   - Press 'r' to rescan (refreshes the network list)
   - Press 'q' to go back to main menu

5. **Wait for Results**
   - Attack progress is displayed in real-time
   - Successful cracks are automatically saved with styled output

6. **View Results**
   - Select option 5 to view all saved passwords
   - Results are saved in `reports/` directory

### Option 6: Fix Root Issues 🔧

If you're experiencing root access problems:

```bash
wifit  # Launch WiFiT
# Select option 6

# The tool will automatically:
# ✓ Diagnose root issues
# ✓ Remove conflicting packages
# ✓ Install required root tools
# ✓ Scan for su binaries
# ✓ Test root access
```

---

## 📁 Output Files

### Results Storage

```
WiFiT/
├── reports/
│   ├── WiFiT_Results.txt      # Human-readable format with styled boxes
│   ├── WiFiT_saved_data.txt   # Quick reference file
│   └── stored.csv              # CSV format for import
└── .WiFiT/
    ├── sessions/               # Attack sessions
    └── pixiewps/               # Pixie Dust data
```

### Sample Output

```
┌─[ WiFiT ]───[ CRACKED ]──────────────────────────────────┐
│                                                            │
│ PIN  : 12345670                                           │
│ PSK  : MySecurePassword123                                │
│ SSID : TargetNetwork                                      │
│                                                            │
└─[ Stay With TuHiN ]──────────────────────────────────────┘

[+] Saved → reports/WiFiT_saved_data.txt
[i] Credentials saved to reports/WiFiT_Results.txt, reports/stored.csv
```

---

## 🧪 Validation Procedure

WiFiT includes a comprehensive hardware validation suite that must pass all 8 phases before stable release.

### Running Validation

```bash
# Navigate to WiFiT directory
cd WiFiT

# Run full validation suite (requires root and test AP)
sudo bash validation/run_all_validation.sh AA:BB:CC:DD:EE:FF
```

### Validation Phases

1. **Environment Setup** - Verifies dependencies, root access, and interface availability
2. **Scanner Validation** - Tests network scanning and WPS detection
3. **PIN Generation** - Validates MAC-based PIN algorithms
4. **Process Management** - Tests wpa_supplicant lifecycle and control
5. **WPS Attack Framework** - Validates attack methods (framework smoke test)
6. **Reporter Validation** - Tests result export and credential storage
7. **PIN Generation Stress** - Generates 1000 PINs to verify algorithm performance
8. **Recovery & Cleanup** - Tests session reload and cleanup procedures

### Validation Limitations

- **Phase 5** performs framework smoke tests only; live WPS transactions must be tested manually with authorized APs
- **Phase 7** measures PIN generation performance, not sustained attack stress
- **Phase 8** tests session reload, not crash recovery or process cleanup
- Strong signal (-60 dBm or better) recommended for eventual live validation
- All validation must be performed on networks you own or have written authorization to test

### Output

Validation generates:
- `validation_logs/master_run_YYYYMMDD_HHMMSS.log` - Complete timestamped log
- `validation_logs/validation_summary_YYYYMMDD_HHMMSS.json` - Machine-readable results
- `validation_logs/validation_report_YYYYMMDD_HHMMSS.html` - Formatted HTML report

---

## 📋 Changelog

### v3.0.0-rc.9 (Current)

**Critical Provenance Improvements:**
- Git provenance now fail-closed: All git commands must succeed or validation aborts
- Comprehensive start/end comparison: SHA, branch, detached state, tag, version, worktree
- Version import explicitly from REPO_ROOT (prevents PATH pollution)
- Git detached HEAD state tracked and compared
- Full provenance in JSON: commit_full, commit_short, branch, detached, tag, clean status
- Full provenance in HTML report: All git metadata displayed including full SHA

**JSON/HTML Enhancements:**
- JSON includes detached HEAD boolean
- HTML displays Git Provenance section with all metadata
- HTML shows full 40-character SHA (not just short)
- HTML shows clean/dirty worktree status

**Version Verification:**
- WiFiT version captured at validation start
- WiFiT version compared at validation end
- Version mismatch fails validation (prevents code changes during run)

**Fail-Closed Security:**
- Git status failure now blocks validation (was: treated as clean)
- Git branch query failure blocks validation
- Git SHA query failure blocks validation
- Version query failure blocks validation

All git and version checks are now mandatory with explicit error messages.

### v3.0.0-rc.8

**Critical Validator & Security Fixes:**
- Fixed Git provenance: Now uses command-scoped `safe.directory` (read-only, no repository mutation)
- Provenance captured at START and END of validation, fails if SHA or worktree changes
- Fixed JSON generation security: Data passed via environment variables, not interpolated into Python source
- Fixed controller cleanup: Now verifies daemon termination with `kill -0` checks, uses `kill -9` if needed
- Fixed BSSID validation: Normalized once upfront, validated format before use
- Added proper error handling for empty JSON generation
- Validation now requires clean worktree at both start and end

**Known Limitations:**
- Phase 5 validation performs framework smoke tests only (not live WPS transactions)
- Phase 7 measures PIN generation performance, not sustained stress testing
- Phase 8 tests session reload, not crash recovery or comprehensive cleanup paths
- Controller cleanup verification is Linux-only (kill -0 not available on all platforms)

### v3.0.0-rc.7

**Release Candidate 7:**
- Git provenance: Mandatory full SHA tracking (was attempting mutation with safe.directory)
- Version centralization: `wifit.py` imports from `wifit_core.__version__`
- Controller exception safety: Wrapped `WPASupplicantController.start()` with try/except cleanup
- 22 new controller tests covering all terminal paths (PIN, null-PIN, PBC, cleanup)
- Fixed test failures on Linux CI:
  - Mock socket exhaustion (StopIteration) - added `socket.timeout()` after event responses
  - M-message event format - changed to "WPS-M5D" (actual wpa_supplicant format)
  - BSSID normalization - tests expect uppercase (normalize_bssid uppercases)
- All 125 tests passing on Linux CI (79.93% coverage)

**Known Issues (fixed in rc.8):**
- Validator aborts after Phase 8 summary (Git provenance collection fails)
- JSON generation interpolates BSSID/Git data into Python source (injection risk)
- Controller cleanup doesn't verify daemon termination

### v3.0.0-rc.6

**Release Blockers Fixed:**
- Fixed PBC timeout clock mismatch (monotonic vs wall time)
- Fixed broadcast PBC BSSID preservation (None no longer converted to "")
- Fixed validation status logic (JSON/HTML/exit code now all require 8/8)
- Removed hardcoded version strings from validation scripts
- Made version/branch/commit dynamic in validation reports

**Known Limitations:**
- Phase 5 validation performs framework tests only (not live WPS transactions)
- Controller test coverage incomplete (comprehensive tests planned for rc.7)

### v3.0.0-rc.5

**Validation Fixes:**
- Fixed shell quoting in Phase 4 (removed apostrophe in error message)
- Fixed broadcast PBC BSSID validation (removed SSID fallback)
- Changed timeout deadlines to use `time.monotonic()` instead of `time.time()`
- Fixed release gate to require ALL 8 phases (was accepting 6/8)
- Made version reporting dynamic from `wifit_core.__version__`

### v3.0.0-rc.4

**Critical Production Fixes:**
- Fixed missing `started_at` timestamp in ALL 15 WPS attack result paths
- Separated wall clock (datetime) for timestamps from monotonic clock for timeouts
- Fixed Bash counter bug in validation scripts (set -e compatibility)
- Fixed ProcessSnapshot constructor to match current API
- Fixed AttackResult test fixtures with consistent timestamps

### v3.0.0-rc.3

**RC2 Blocking Issues Fixed:**
- Added ATTACH command to wpa_supplicant controller
- Distinguished null PIN from empty PIN (separate methods)
- Fixed pixiewps success detection (require PIN extraction + exit 0)
- Corrected all validation script API calls
- Integrated RC2 modules into wifit.py smart_bruteforce
- Removed || true from CI quality gates
- Fixed Windows file permission issue in BruteforceSession.save()

### v3.0.0-rc.1

**Initial Release Candidate:**
- Complete rewrite with production-grade architecture
- Proper WPS attack via wpa_supplicant control interface
- Validated PIN/null-PIN/empty-PIN/zero-PIN/PBC methods
- Timeout handling with first-half detection
- Session management and credential extraction
- Comprehensive test suite (103 tests)
- Hardware validation framework

---

## 🛠️ Troubleshooting

### Common Issues

**1. "No superuser binary detected"**
```bash
# Solution: Use Option 6 (Fix Root Issues)
wifit
# Select option 6 from menu

# Or manually:
pkg install root-repo tsu -y
wifit  # Grant permission when prompted
```

**2. "No WPS networks found"**
```bash
# WiFiT now provides retry option:
# - Press Enter to scan again
# - Press 'q' to return to menu

# Manual troubleshooting:
# - Ensure WiFi is enabled on your device
# - Move closer to access points
# - Check if networks actually have WPS enabled
# - Try different locations
```

**3. "Root access not working"**
```bash
# Check if Magisk/KernelSU is installed
# Open Magisk app → Check Termux permissions

# Test one-shot root access manually:
sudo id  # Should show uid=0(root) and return to the normal shell
```

**4. "Permission denied"**
```bash
# Make sure you granted Termux root access
# In Magisk/KernelSU:
# - Find Termux
# - Grant superuser permission
# - Check "Remember choice"
```

**5. "Interface not found"**
```bash
# Check available interfaces
ip link show

# WiFi interface is usually wlan0
```

**6. "Command not found: wifit"**
```bash
# Restart Termux
exit  # Close Termux
# Open Termux again

# Or reinstall
cd WiFiT
bash install.sh
```

### Get Help

- Open an issue: [GitHub Issues](https://github.com/TuHiN22/WiFiT/issues)
- Check existing issues for solutions
- Include error messages and system info

---

## 🔧 Advanced Configuration

### Custom Interface

Edit `wifit.py` to change default interface:

```python
def _get_wifi_interface(self):
    return "wlan1"  # Change to your interface
```

### Attack Timeout

Modify timeout in `MenuHandler` class:

```python
# Default is 30 seconds per target
timeout = 60  # Increase to 60 seconds
```

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork the repository**
2. **Create your feature branch** (`git checkout -b feature/AmazingFeature`)
3. **Commit your changes** (`git commit -m 'Add some AmazingFeature'`)
4. **Push to the branch** (`git push origin feature/AmazingFeature`)
5. **Open a Pull Request**

### Development Setup

```bash
git clone https://github.com/TuHiN22/WiFiT.git
cd WiFiT
# Make your changes
python3 wifit.py
```

---

## 📜 Credits

WiFiT is a hybrid tool that combines concepts and code from:

- **W8RootWifiHKV2** - Menu system and UI design
- **FARHAN-Shot** - Modern architecture and clean code structure
- **OneShotPin** - WPS PIN algorithms
- **Pixiewps** - Pixie Dust implementation

### Author

- **TuHiN** - Initial work and hybrid development

---

## ⚖️ Legal Disclaimer

**IMPORTANT: READ BEFORE USING**

This tool is created for **educational and authorized testing purposes only**.

### Legal Usage

✅ **ALLOWED:**
- Testing your own network
- Authorized penetration testing with written permission
- Educational research in controlled environments
- Security auditing of networks you own or have permission to test

❌ **NOT ALLOWED:**
- Accessing networks without explicit authorization
- Unauthorized penetration testing
- Any illegal activity

### Responsibility

- The author is **NOT responsible** for any misuse of this tool
- Users are **solely responsible** for their actions
- Unauthorized access to computer networks is **illegal** in most countries
- Violations can result in **criminal prosecution**

### Ethical Use

By using WiFiT, you agree to:
1. Only test networks you own or have written permission to test
2. Respect privacy and confidentiality
3. Follow all applicable laws and regulations
4. Use the tool responsibly and ethically

**Use this tool at your own risk. Be ethical. Be legal.**

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2026 TuHiN

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🌟 Star History

If you find WiFiT useful, please consider giving it a star ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=TuHiN22/WiFiT&type=Date)](https://star-history.com/#TuHiN22/WiFiT&Date)

---

## 📞 Contact

- **GitHub**: [@TuHiN22](https://github.com/TuHiN22)
- **Project Link**: [https://github.com/TuHiN22/WiFiT](https://github.com/TuHiN22/WiFiT)

---

<div align="center">

**Made with ❤️ by TuHiN**

*For educational purposes only. Use responsibly.*

</div>
