# WiFiT Quick Start Guide

## 🚀 দ্রুত শুরু করুন (Bangla)

### ১. ইনস্টলেশন

```bash
# Repository clone করুন
git clone https://github.com/TuHiN22/WiFiT.git
cd WiFiT

# Installer চালান (root হিসেবে)
chmod +x install.sh
sudo ./install.sh
```

### ২. চালান

```bash
# WiFiT শুরু করুন
sudo wifit
```

### ৩. Menu থেকে বেছে নিন

```
[1] Auto Attack    - সব network স্বয়ংক্রিয়ভাবে attack করুন
[2] Pixie Dust     - দ্রুত PIN recovery
[3] Brute Force    - পরিকল্পিত PIN testing
[4] Smart Attack   - AI সহায়তায় attack
[5] Passwords দেখুন - সব cracked passwords
[6] Exit           - বের হন
```

### ৪. Network Select করুন

```
WPS-Enabled Networks:
#    BSSID              ESSID                     PWR      Status
──────────────────────────────────────────────────────────────────
1)   AA:BB:CC:DD:EE:FF HomeWiFi                  -45      OPEN
2)   11:22:33:44:55:66 OfficeNet                 -67      OPEN
3)   99:88:77:66:55:44 GuestWiFi                 -52      LOCKED

[?] Select network number: 1
```

### ৫. Results দেখুন

সফল attack এর পর:
```
[+] SUCCESS!
[+] WPS PIN: '12345670'
[+] WPA PSK: 'MyPassword123'
[+] AP SSID: 'HomeWiFi'
[+] Credentials saved to reports/WiFiT_Results.txt
```

---

## 🚀 Quick Start (English)

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/TuHiN22/WiFiT.git
cd WiFiT

# Run installer (as root)
chmod +x install.sh
sudo ./install.sh
```

### 2. Run WiFiT

```bash
# Start WiFiT
sudo wifit
```

### 3. Choose from Menu

```
[1] Auto Attack     - Automatically attack all networks
[2] Pixie Dust      - Fast PIN recovery
[3] Brute Force     - Systematic PIN testing
[4] Smart Attack    - AI-enhanced attack
[5] View Passwords  - See all cracked passwords
[6] Exit            - Quit the program
```

### 4. Select Network

```
WPS-Enabled Networks:
#    BSSID              ESSID                     PWR      Status
──────────────────────────────────────────────────────────────────
1)   AA:BB:CC:DD:EE:FF HomeWiFi                  -45      OPEN
2)   11:22:33:44:55:66 OfficeNet                 -67      OPEN
3)   99:88:77:66:55:44 GuestWiFi                 -52      LOCKED

[?] Select network number: 1
```

### 5. View Results

After successful attack:
```
[+] SUCCESS!
[+] WPS PIN: '12345670'
[+] WPA PSK: 'MyPassword123'
[+] AP SSID: 'HomeWiFi'
[+] Credentials saved to reports/WiFiT_Results.txt
```

---

## 💡 Tips & Tricks

### Best Practices

1. **Option 1 (Auto Attack) দিয়ে শুরু করুন**
   - নতুন users এর জন্য সবচেয়ে সহজ
   - স্বয়ংক্রিয়ভাবে সব networks try করে

2. **Signal Strength গুরুত্বপূর্ণ**
   - -30 to -50 dBm = Excellent
   - -50 to -70 dBm = Good
   - -70 to -85 dBm = Fair
   - Below -85 dBm = Poor

3. **WPS Locked Networks Skip করুন**
   - LOCKED status মানে WPS বন্ধ
   - এসব networks attack করা যাবে না

4. **Results Regular Check করুন**
   - Option 5 দিয়ে saved passwords দেখুন
   - `reports/` folder এ সব কিছু save হয়

### Troubleshooting

**Problem: "No WPS networks found"**
```bash
Solution:
- WiFi adapter ঠিক আছে কিনা check করুন
- কাছাকাছি networks আছে কিনা নিশ্চিত করুন
- Different location এ try করুন
```

**Problem: "Permission denied"**
```bash
Solution:
- Root হিসেবে চালান: sudo wifit
- Root access আছে কিনা check করুন
```

**Problem: "Interface not found"**
```bash
Solution:
# Available interfaces দেখুন
iwconfig
# বা
ip link show

# WiFiT script edit করে interface change করুন
```

### Advanced Usage

#### Custom Interface
```bash
# wifit.py file edit করুন
def _get_wifi_interface(self):
    return "wlan1"  # আপনার interface name
```

#### Results Location
```bash
# Results এখানে save হয়:
./reports/WiFiT_Results.txt    # Human-readable
./reports/stored.csv            # CSV format

# View করুন:
cat reports/WiFiT_Results.txt
```

#### Multiple Sessions
```bash
# একসাথে অনেকগুলো WiFiT চালাতে পারবেন:
sudo wifit  # Terminal 1
sudo wifit  # Terminal 2 (different interface)
```

---

## 📊 Attack Success Rates

### Pixie Dust Attack
- **Success Rate**: 60-80% on vulnerable routers
- **Time**: 10 seconds - 5 minutes
- **Best For**: Modern routers with WPS enabled

### Brute Force Attack
- **Success Rate**: 20-40% (depends on PIN)
- **Time**: 1 hour - several hours
- **Best For**: Routers with weak PIN algorithms

### Smart Attack
- **Success Rate**: 70-90% (combined)
- **Time**: 30 seconds - 10 minutes
- **Best For**: Unknown routers (tries both methods)

---

## 🎯 Common Scenarios

### Scenario 1: Home Network Testing
```
1. sudo wifit
2. Select [2] Pixie Dust Attack
3. Choose your home network
4. Wait 30-60 seconds
5. If successful, password saved automatically
```

### Scenario 2: Multiple Networks
```
1. sudo wifit
2. Select [1] Auto Attack
3. Let it scan all networks
4. Sit back and watch
5. Check results with option [5]
```

### Scenario 3: Specific Target
```
1. sudo wifit
2. Select [4] Smart Attack
3. Choose target network
4. Best chance of success (tries all methods)
```

---

## ⚠️ Important Notes

### Legal Requirements
- ✅ শুধুমাত্র নিজের network test করুন
- ✅ অনুমতি নিয়ে authorized testing করুন
- ❌ অন্যের network এ unauthorized access নিবেন না

### Safety
- সবসময় ethical ভাবে tool use করুন
- Privacy respect করুন
- আইন মেনে চলুন

### Limitations
- সব routers WPS support করে না
- WPS locked networks attack করা যায় না
- দুর্বল signal এ success rate কম

---

## 📚 Additional Resources

### Documentation
- Full README: [README.md](README.md)
- Project Summary: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)
- License: [LICENSE](LICENSE)

### Links
- GitHub: https://github.com/TuHiN22/WiFiT
- Issues: https://github.com/TuHiN22/WiFiT/issues

### Support
- যেকোনো সমস্যা হলে GitHub Issue open করুন
- Error message এবং system info দিন
- Community সাহায্য করবে

---

## 🎓 Learning Resources

### WPS Security
- [WPS Protocol Overview](https://en.wikipedia.org/wiki/Wi-Fi_Protected_Setup)
- [Pixie Dust Attack Explained](https://forums.kali.org/showthread.php?24286-WPS-Pixie-Dust-Attack-(Offline-WPS-Attack))

### WiFi Security
- [WiFi Security Best Practices](https://www.wi-fi.org/discover-wi-fi/security)
- [WPA/WPA2 Security](https://en.wikipedia.org/wiki/Wi-Fi_Protected_Access)

---

<div align="center">

**Happy Testing! 🎉**

*Remember: Use responsibly and ethically*

Made with ❤️ by TuHiN

</div>
