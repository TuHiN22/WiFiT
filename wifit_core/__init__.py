"""WiFiT Core - Professional WPS Testing Toolkit

A modular, testable implementation of WPS security assessment tools.
"""

__version__ = "3.0.0-rc.6"

from .models import (
    AccessPoint,
    AttackMethod,
    AttackOutcome,
    AttackResult,
    SecurityMode,
    WPSVersion,
    WPSVersionEvidence,
)
from .pin_generator import MACAddress, PINGenerator, generate_pin, get_likely_pins, wps_checksum
from .pixie_dust import PixiewpsParameters, PixiewpsResult, run_pixiewps
from .platform import PlatformManager, WirelessInterface
from .process_manager import ProcessManager, ProcessSnapshot
from .reporter import ReportFormat, ResultReporter
from .runner import CommandResult, CommandRunner
from .scanner import WiFiScanner, parse_iw_scan
from .vulnerability import WSCVulnerabilityDatabase, annotate_access_points
from .wps_attack import WPASupplicantController, try_pbc_attack, try_pin_attack
from .wps_bruteforce import BruteforceProgress, BruteforceSession, enumerate_all_pins

__all__ = [
    "AccessPoint",
    "AttackMethod",
    "AttackOutcome",
    "AttackResult",
    "BruteforceProgress",
    "BruteforceSession",
    "CommandResult",
    "CommandRunner",
    "MACAddress",
    "PINGenerator",
    "PixiewpsParameters",
    "PixiewpsResult",
    "PlatformManager",
    "ProcessManager",
    "ProcessSnapshot",
    "ReportFormat",
    "ResultReporter",
    "SecurityMode",
    "WPASupplicantController",
    "WiFiScanner",
    "WPSVersion",
    "WPSVersionEvidence",
    "WSCVulnerabilityDatabase",
    "WirelessInterface",
    "annotate_access_points",
    "enumerate_all_pins",
    "generate_pin",
    "get_likely_pins",
    "parse_iw_scan",
    "run_pixiewps",
    "try_pbc_attack",
    "try_pin_attack",
    "wps_checksum",
]
