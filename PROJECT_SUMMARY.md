# WiFiT Project Summary

## Overview
WiFiT হল একটি professional WPS penetration testing tool যা দুটি GitHub repository থেকে সেরা features নিয়ে তৈরি করা হয়েছে।

## Source Repositories

### 1. W8RootWifiHKV2 (পুরোনো/Base Script)
- **URL**: https://github.com/W8SOJIB/W8RootWifiHKV2
- **কি নেওয়া হয়েছে**:
  - সুন্দর menu system (options 1-7)
  - Menu style এবং execution style
  - UI/UX presentation
  - Options 2, 3, 4 এর functionality:
    - Option 2: Pixie Dust Attack
    - Option 3: Brute Force Attack
    - Option 4: Smart/AI PIN Attack

### 2. FARHAN-Shot (Updated Script)
- **URL**: https://github.com/frnAlt/FARHAN-Shot
- **কি নেওয়া হয়েছে**:
  - Modern modular architecture
  - Clean code structure
  - Professional logging system
  - Efficient implementation
  - Updated WPS attack algorithms

## WiFiT Features (Hybrid)

### Main Menu (6 Options)
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

### Key Components

1. **NetworkAddress Class**
   - MAC address manipulation
   - Integer/String conversion

2. **WPSpin Class**
   - 20+ PIN generation algorithms
   - Vendor-specific algorithms
   - Static and dynamic PINs

3. **Companion Class**
   - Main attack handler
   - WPA supplicant integration
   - Pixiewps execution
   - Result saving

4. **WiFiScanner Class**
   - Network discovery
   - WPS detection
   - Signal strength sorting

5. **MenuHandler Class**
   - Interactive menu system
   - User input handling
   - Attack coordination

### Attack Modes

#### Option 1: Auto Attack
- স্বয়ংক্রিয়ভাবে সব WPS networks scan করে
- প্রতিটি target এ Pixie Dust attack চালায়
- 30-second timeout per target
- সম্পূর্ণ summary দেখায়

#### Option 2: Pixie Dust Attack
- দ্রুত WPS PIN recovery
- Weak random number generator exploit
- Highest success rate

#### Option 3: Brute Force Attack
- Systematic PIN testing
- Smart PIN generation
- MAC-based algorithms
- Progress tracking with ETA

#### Option 4: Smart Attack
- Pixie Dust + Brute Force combination
- Automatic fallback
- AI-enhanced PIN prediction

#### Option 5: View Saved Passwords
- সব cracked credentials দেখায়
- TXT এবং CSV format
- Timestamp সহ

## Technical Details

### File Structure
```
WiFiT/
├── wifit.py              # Main script (1600+ lines)
├── install.sh            # Installation script
├── README.md             # Documentation
├── LICENSE               # MIT License
├── PROJECT_SUMMARY.md    # This file
└── reports/              # Results storage
    ├── WiFiT_Results.txt
    └── stored.csv
```

### Dependencies
- Python 3.6+
- wpa_supplicant
- pixiewps
- iw/iwlist
- wireless-tools

### Branding
- **Author**: TuHiN (সব জায়গায় replace করা হয়েছে)
- **Command**: `wifit` (পুরো menu launch করে)
- **Colors**: Cyan, Green, Yellow theme
- **Banner**: Professional WiFiT branding

## Installation

```bash
# Clone repository
git clone https://github.com/TuHiN22/WiFiT.git
cd WiFiT

# Install
chmod +x install.sh
sudo ./install.sh

# Run
sudo wifit
```

## Key Improvements

### From Old Script
✅ Menu system এবং execution style রাখা হয়েছে
✅ Options 2, 3, 4 functionality integrate করা হয়েছে
✅ UI/UX design maintain করা হয়েছে

### From Updated Script
✅ Modern code structure
✅ Clean implementation
✅ Professional error handling
✅ Better logging system

### New Additions
✅ Full TuHiN branding
✅ Professional README with badges
✅ Easy installation script
✅ GitHub-ready repository
✅ Simplified 6-option menu
✅ Combined best of both worlds

## Comparison

| Feature | Old Script | Updated Script | WiFiT (Hybrid) |
|---------|-----------|----------------|----------------|
| Menu System | ✅ Beautiful | ❌ CLI only | ✅ Beautiful |
| Code Quality | ⚠️ Complex | ✅ Clean | ✅ Clean |
| Auto Attack | ✅ Yes | ❌ No | ✅ Enhanced |
| Pixie Dust | ✅ Yes | ✅ Yes | ✅ Yes |
| Brute Force | ✅ Basic | ✅ Advanced | ✅ Smart |
| PIN Algorithms | ✅ Many | ⚠️ Limited | ✅ Many |
| UI/UX | ✅ Excellent | ⚠️ Basic | ✅ Excellent |
| Documentation | ⚠️ Limited | ✅ Good | ✅ Comprehensive |
| Installation | ⚠️ Manual | ⚠️ Manual | ✅ Automated |

## Usage Example

```bash
# Run WiFiT
sudo wifit

# Select option 1 for auto attack
[?] Select option (1-6): 1

# Watch as it scans and attacks all networks
[*] Found 15 WPS networks
[1/15] 🎯 Attacking: HomeWiFi (AA:BB:CC:DD:EE:FF)
[+] ✅ Success!

# View results
[?] Select option (1-6): 5
```

## Success Criteria ✅

✅ দুই scripts blend করা হয়েছে
✅ Menu style পুরোনো script এর মতো
✅ Core code updated script এর
✅ Options 2, 3, 4 কাজ করছে
✅ Author name: TuHiN
✅ Command: wifit
✅ Full new branding
✅ Professional README
✅ Installation script
✅ GitHub repository ready

## Repository Links

- **WiFiT (This Project)**: https://github.com/TuHiN22/WiFiT
- **Old Script (W8RootWifiHKV2)**: https://github.com/W8SOJIB/W8RootWifiHKV2
- **Updated Script (FARHAN-Shot)**: https://github.com/frnAlt/FARHAN-Shot

## Credits

WiFiT combines the best features from:
- W8RootWifiHKV2 by W8SOJIB (Menu system and UI)
- FARHAN-Shot by frnAlt (Modern architecture)
- Author: TuHiN (Hybrid development)

## License

MIT License - Free to use, modify, and distribute

---

**তৈরি করা হয়েছে: 5 August 2026**
**Author: TuHiN**
**Version: 1.0.0**
