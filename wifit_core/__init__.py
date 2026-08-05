"""WiFiT Core - Professional WPS Testing Toolkit

A modular, testable implementation of WPS security assessment tools.
"""

__version__ = "3.0.0-rc.1"

from .models import (
    AccessPoint,
    AttackMethod,
    AttackOutcome,
    AttackResult,
    SecurityMode,
    WPSVersion,
    WPSVersionEvidence,
)
from .platform import PlatformManager, WirelessInterface
from .process_manager import ProcessManager, ProcessSnapshot
from .reporter import ReportFormat, ResultReporter
from .runner import CommandRunner, CommandResult
from .scanner import WiFiScanner, parse_iw_scan
from .vulnerability import WSCVulnerabilityDatabase, annotate_access_points

__all__ = [
    "AccessPoint",
    "AttackMethod",
    "AttackOutcome",
    "AttackResult",
    "CommandResult",
    "CommandRunner",
    "PlatformManager",
    "ProcessManager",
    "ProcessSnapshot",
    "ReportFormat",
    "ResultReporter",
    "SecurityMode",
    "WiFiScanner",
    "WPSVersion",
    "WPSVersionEvidence",
    "WSCVulnerabilityDatabase",
    "WirelessInterface",
    "annotate_access_points",
    "parse_iw_scan",
]
