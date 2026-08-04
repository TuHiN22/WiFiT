# WiFiT - Professional WPS Testing Toolkit

<div align="center">

```
╔══════════════════════════════════════════════════════════════╗
║                    🛡️  WiFiT v1.0.0                         ║
║              Professional WPS Testing Toolkit                ║
║                      Author: TuHiN                           ║
╚══════════════════════════════════════════════════════════════╝
```

[![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Termux-lightgrey.svg)](https://github.com/TuHiN22/WiFiT)

**A powerful hybrid WiFi penetration testing tool combining advanced WPS attack methods**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Legal](#%EF%B8%8F-legal-disclaimer)

</div>

---

## 🎯 About

WiFiT is a professional WPS (Wi-Fi Protected Setup) penetration testing toolkit that combines the best features from multiple WiFi security testing tools. It features an intuitive menu-driven interface with multiple attack modes and automated network discovery.

### 🌟 Key Highlights

- **🚀 Auto Attack Mode** - Automatically scan and attack all WPS-enabled networks
- **⚡ Pixie Dust Attack** - Fast WPS PIN recovery using known vulnerabilities
- **💪 Brute Force Mode** - Systematic PIN testing with smart algorithms
- **🤖 Smart Attack** - AI-enhanced PIN prediction and recovery
- **📊 Comprehensive Logging** - All results saved with timestamps
- **🎨 Beautiful UI** - Color-coded interface with progress indicators

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

### Additional Features

- **Network Scanner** - Displays WPS-enabled networks with signal strength
- **Password Manager** - View all cracked credentials
- **Multiple Export Formats** - TXT and CSV output
- **Session Management** - Resume interrupted attacks
- **MAC Address Support** - Vendor-specific algorithms for major brands

---

## 📋 Requirements

### System Requirements

- **OS**: Linux (Kali, Ubuntu, Debian) or Android (Termux)
- **Python**: 3.6 or higher
- **Root Access**: Required for WiFi operations

### Dependencies

- `python3` - Python interpreter
- `wpa_supplicant` - WPS protocol handler
- `pixiewps` - Pixie Dust attack tool
- `iw` or `iwlist` - Wireless scanning
- `wireless-tools` - WiFi utilities

### Python Packages (Optional)

- `pyfiglet` - ASCII art banners
- `psutil` - System information

---

## 🚀 Installation

### Quick Install (Recommended)

```bash
# Clone the repository
git clone https://github.com/TuHiN22/WiFiT.git
cd WiFiT

# Make installer executable
chmod +x install.sh

# Run installer as root
sudo ./install.sh
```

### Manual Installation

```bash
# Install dependencies (Debian/Ubuntu)
sudo apt-get update
sudo apt-get install -y python3 wpasupplicant pixiewps iw wireless-tools

# Install Python packages
pip3 install pyfiglet psutil

# Make script executable
chmod +x wifit.py

# Create symbolic link
sudo ln -s $(pwd)/wifit.py /usr/local/bin/wifit
```

### Termux Installation (Android)

```bash
# Install Termux from F-Droid (not Play Store)
# Open Termux and run:

pkg update && pkg upgrade
pkg install python git root-repo
pkg install tsu

# Clone and install
git clone https://github.com/TuHiN22/WiFiT.git
cd WiFiT
chmod +x install.sh
sudo ./install.sh
```

---

## 📖 Usage

### Basic Usage

```bash
# Start WiFiT (must run as root)
sudo wifit
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
║  [6] 🚪 Exit                                                ║
╚══════════════════════════════════════════════════════════════╝
```

### Step-by-Step Guide

1. **Select Attack Mode**
   - Choose option 1-4 based on your needs
   - Option 1 (Auto Attack) is recommended for beginners

2. **Scan Networks**
   - WiFiT will scan for WPS-enabled networks
   - Networks are sorted by signal strength

3. **Select Target**
   - Enter the number of target network
   - Press 'r' to rescan
   - Press 'q' to go back

4. **Wait for Results**
   - Attack progress is displayed in real-time
   - Successful cracks are automatically saved

5. **View Results**
   - Select option 5 to view all saved passwords
   - Results are saved in `reports/` directory

---

## 📁 Output Files

### Results Storage

```
WiFiT/
├── reports/
│   ├── WiFiT_Results.txt      # Human-readable format
│   └── stored.csv              # CSV format for import
└── .WiFiT/
    ├── sessions/               # Attack sessions
    └── pixiewps/               # Pixie Dust data
```

### Sample Output

```
═══════════════════════════════════════
WiFiT Attack Result - 05.08.2026 14:30
═══════════════════════════════════════
BSSID: AA:BB:CC:DD:EE:FF
ESSID: TargetNetwork
WPS PIN: 12345670
WPA PSK: MySecurePassword123
═══════════════════════════════════════
```

---

## 🛠️ Troubleshooting

### Common Issues

**1. "No WPS networks found"**
- Ensure your WiFi adapter supports monitor mode
- Check if networks actually have WPS enabled
- Try moving closer to access points

**2. "wpa_supplicant error"**
```bash
# Kill existing wpa_supplicant processes
sudo killall wpa_supplicant
# Try again
```

**3. "Permission denied"**
```bash
# Ensure you're running as root
sudo wifit
```

**4. "Interface not found"**
```bash
# Check available interfaces
iwconfig
# or
ip link show
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
