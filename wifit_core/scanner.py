"""Reliable ``iw`` scan execution and parsing.

The parser is intentionally independent from subprocess execution so recorded
``iw`` fixtures can be tested without wireless hardware or root privileges.
"""

from __future__ import annotations

import re
import subprocess
import time
from collections.abc import Callable
from typing import Any

from .models import (
    AccessPoint,
    SecurityMode,
    WPSVersion,
    WPSVersionEvidence,
)
from .runner import CommandError, CommandRunner, CommandTimeoutError

_BSS_HEADER_RE = re.compile(r"^\s*BSS\s+([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})(?=\s|\()")
_FREQUENCY_RE = re.compile(r"^\s*freq:\s*(\d+)\s*$", re.IGNORECASE)
_SIGNAL_RE = re.compile(
    r"^\s*signal:\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*dBm\b",
    re.IGNORECASE,
)
_CHANNEL_RES = (
    re.compile(r"\bDS Parameter set:\s*channel\s+(\d+)\b", re.IGNORECASE),
    re.compile(r"\bprimary channel:\s*(\d+)\b", re.IGNORECASE),
)
_WPS_HEADER_RE = re.compile(r"^\s*WPS:\s*(?:\*\s*)?Version:\s*([^\s(]+)", re.IGNORECASE)
_WPS_MARKER_RE = re.compile(r"^\s*WPS:\s*$", re.IGNORECASE)
_WPS_VERSION2_RE = re.compile(r"^\s*\*?\s*Version2:\s*([^\s(]+)", re.IGNORECASE)
_WPS_NESTED_VERSION_RE = re.compile(r"^\s*\*\s*Version:\s*([^\s(]+)", re.IGNORECASE)
_WPS_LOCK_RE = re.compile(r"^\s*\*?\s*AP setup locked:\s*([^\s(]+)", re.IGNORECASE)
_WSC_FIELD_RE = re.compile(
    r"^\s*\*?\s*(Manufacturer|Model Number|Model|Device name):\s*(.*)$",
    re.IGNORECASE,
)


class ScanError(RuntimeError):
    """Raised after all bounded ``iw`` scan attempts fail."""

    def __init__(self, interface: str, attempts: int, reason: str) -> None:
        self.interface = interface
        self.attempts = attempts
        self.reason = reason
        super().__init__(
            f"iw scan failed on {interface!r} after {attempts} "
            f"attempt{'s' if attempts != 1 else ''}: {reason}"
        )


def frequency_to_channel(frequency_mhz: int | None) -> int | None:
    """Map common 2.4/5/6/60 GHz center frequencies to channel numbers."""

    if frequency_mhz is None:
        return None
    if frequency_mhz == 2484:
        return 14
    if frequency_mhz == 5935:
        return 2
    if 2412 <= frequency_mhz <= 2472 and (frequency_mhz - 2407) % 5 == 0:
        return (frequency_mhz - 2407) // 5
    if 5000 <= frequency_mhz <= 5895 and (frequency_mhz - 5000) % 5 == 0:
        return (frequency_mhz - 5000) // 5
    if 4910 <= frequency_mhz <= 4980 and (frequency_mhz - 4000) % 5 == 0:
        return (frequency_mhz - 4000) // 5
    if 5955 <= frequency_mhz <= 7115 and (frequency_mhz - 5950) % 5 == 0:
        return (frequency_mhz - 5950) // 5
    if 58320 <= frequency_mhz <= 70200 and (frequency_mhz - 56160) % 2160 == 0:
        return (frequency_mhz - 56160) // 2160
    return None


def _decode_iw_text(value: str) -> str:
    """Decode iw's ``\\xNN`` and simple backslash escapes as UTF-8."""

    decoded = bytearray()
    escape_bytes = {"n": b"\n", "r": b"\r", "t": b"\t", "\\": b"\\"}
    index = 0
    while index < len(value):
        if value[index] != "\\":
            decoded.extend(value[index].encode("utf-8"))
            index += 1
            continue

        if index + 3 < len(value) and value[index + 1] == "x":
            candidate = value[index + 2 : index + 4]
            if re.fullmatch(r"[0-9A-Fa-f]{2}", candidate):
                decoded.append(int(candidate, 16))
                index += 4
                continue

        if index + 1 < len(value) and value[index + 1] in escape_bytes:
            decoded.extend(escape_bytes[value[index + 1]])
            index += 2
            continue

        decoded.extend(b"\\")
        index += 1

    return decoded.decode("utf-8", errors="replace")


def _parse_version(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    token = value.strip().rstrip(",;")
    try:
        if token.lower().startswith("0x"):
            numeric = int(token, 16)
            return numeric >> 4, numeric & 0x0F
    except ValueError:
        return None

    match = re.search(r"(\d+)(?:\.(\d+))?", token)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2) or 0)


def _parse_lock(value: str) -> bool | None:
    normalized = value.strip().casefold()
    if normalized in {"yes", "true", "locked", "on"}:
        return True
    if normalized in {"no", "false", "unlocked", "off"}:
        return False
    try:
        return int(normalized, 0) != 0
    except ValueError:
        return None


def _classify_security(
    *, has_privacy: bool, has_wpa: bool, has_rsn: bool, auth_lines: list[str]
) -> tuple[SecurityMode, bool, bool]:
    suites = " ".join(auth_lines).upper()
    has_sae = re.search(r"\bSAE\b", suites) is not None
    has_owe = re.search(r"\bOWE\b", suites) is not None
    has_psk = re.search(r"\bPSK\b", suites) is not None
    wpa3 = has_sae or has_owe
    transition = has_sae and has_psk

    if transition:
        return SecurityMode.WPA2_WPA3, True, True
    if wpa3:
        return SecurityMode.WPA3, True, False
    if has_wpa and has_rsn:
        return SecurityMode.WPA_WPA2, False, False
    if has_rsn:
        return SecurityMode.WPA2, False, False
    if has_wpa:
        return SecurityMode.WPA, False, False
    if has_privacy:
        return SecurityMode.WEP, False, False
    return SecurityMode.OPEN, False, False


def _parse_bss_block(bssid: str, lines: list[str]) -> AccessPoint:
    ssid = "<hidden>"
    signal_dbm: float | None = None
    frequency_mhz: int | None = None
    channel: int | None = None
    has_privacy = False
    has_wpa = False
    has_rsn = False
    auth_lines: list[str] = []

    wps = False
    base_wps_version: tuple[int, int] | None = None
    version2: tuple[int, int] | None = None
    wps_locked: bool | None = None
    inside_wps = False
    wsc_fields = {
        "manufacturer": "",
        "model": "",
        "model number": "",
        "device name": "",
    }

    for raw_line in lines:
        stripped = raw_line.strip()
        lowered = stripped.casefold()

        frequency_match = _FREQUENCY_RE.match(raw_line)
        if frequency_match:
            frequency_mhz = int(frequency_match.group(1))
            continue

        signal_match = _SIGNAL_RE.match(raw_line)
        if signal_match:
            signal_dbm = float(signal_match.group(1))
            continue

        for channel_re in _CHANNEL_RES:
            channel_match = channel_re.search(raw_line)
            if channel_match:
                channel = int(channel_match.group(1))
                break

        if lowered.startswith("ssid:"):
            raw_ssid = stripped.partition(":")[2].lstrip()
            decoded_ssid = _decode_iw_text(raw_ssid)
            ssid = decoded_ssid if decoded_ssid.strip("\x00 \t\r\n") else "<hidden>"
            continue

        if lowered.startswith("capability:"):
            has_privacy = "privacy" in lowered
            inside_wps = False
            continue

        if stripped.upper().startswith("RSN:"):
            has_rsn = True
            inside_wps = False
            continue
        if stripped.upper().startswith("WPA:"):
            has_wpa = True
            inside_wps = False
            continue
        if "authentication suites:" in lowered:
            auth_lines.append(stripped.partition(":")[2])

        wps_header = _WPS_HEADER_RE.match(raw_line)
        if wps_header:
            wps = True
            inside_wps = True
            base_wps_version = _parse_version(wps_header.group(1))
            continue
        if _WPS_MARKER_RE.match(raw_line):
            wps = True
            inside_wps = True
            continue

        version2_match = _WPS_VERSION2_RE.match(raw_line)
        if wps and version2_match:
            version2 = _parse_version(version2_match.group(1))
            continue

        nested_version_match = _WPS_NESTED_VERSION_RE.match(raw_line)
        if inside_wps and nested_version_match and base_wps_version is None:
            base_wps_version = _parse_version(nested_version_match.group(1))
            continue

        lock_match = _WPS_LOCK_RE.match(raw_line)
        if wps and lock_match:
            wps_locked = _parse_lock(lock_match.group(1))
            continue

        wsc_match = _WSC_FIELD_RE.match(raw_line)
        if wps and wsc_match:
            key = wsc_match.group(1).casefold()
            wsc_fields[key] = _decode_iw_text(wsc_match.group(2).strip())

    security, wpa3, transition = _classify_security(
        has_privacy=has_privacy,
        has_wpa=has_wpa,
        has_rsn=has_rsn,
        auth_lines=auth_lines,
    )

    wps_version: WPSVersion | None = None
    evidence = WPSVersionEvidence.UNKNOWN
    if wps:
        if version2 is not None:
            if version2[0] >= 2:
                wps_version = WPSVersion.VERSION_2
            elif version2[0] == 1:
                wps_version = WPSVersion.VERSION_1
            else:
                wps_version = WPSVersion.UNKNOWN
            evidence = WPSVersionEvidence.CONFIRMED
        elif base_wps_version is not None and base_wps_version[0] >= 2:
            wps_version = WPSVersion.VERSION_2
            evidence = WPSVersionEvidence.CONFIRMED
        elif base_wps_version is not None and base_wps_version[0] == 1:
            # WPS 2 APs retain the base Version 1.0 attribute.  Version 1 is
            # therefore inferred only when a Version2 vendor extension is absent.
            wps_version = WPSVersion.VERSION_1
            evidence = WPSVersionEvidence.INFERRED
        else:
            wps_version = WPSVersion.UNKNOWN

    return AccessPoint(
        bssid=bssid,
        ssid=ssid,
        signal_dbm=signal_dbm,
        channel=channel if channel is not None else frequency_to_channel(frequency_mhz),
        frequency_mhz=frequency_mhz,
        wps=wps,
        wps_version=wps_version,
        wps_version_evidence=evidence,
        wps_locked=wps_locked,
        security=security,
        wpa3=wpa3,
        wpa3_transition=transition,
        wsc_manufacturer=wsc_fields["manufacturer"],
        wsc_model_name=wsc_fields["model"],
        wsc_model_number=wsc_fields["model number"],
        wsc_device_name=wsc_fields["device name"],
    )


def parse_iw_scan(output: str) -> list[AccessPoint]:
    """Parse all valid BSS blocks, returning strongest access points first."""

    parsed: list[AccessPoint] = []
    current_bssid: str | None = None
    current_lines: list[str] = []

    for line in output.splitlines():
        header = _BSS_HEADER_RE.match(line)
        if header:
            if current_bssid is not None:
                parsed.append(_parse_bss_block(current_bssid, current_lines))
            current_bssid = header.group(1)
            current_lines = []
            continue
        if current_bssid is not None:
            current_lines.append(line)

    if current_bssid is not None:
        parsed.append(_parse_bss_block(current_bssid, current_lines))

    parsed.sort(
        key=lambda access_point: (
            access_point.signal_dbm is not None,
            access_point.signal_dbm if access_point.signal_dbm is not None else float("-inf"),
        ),
        reverse=True,
    )
    return parsed


# Descriptive alias retained for callers that prefer parser-specific naming.
parse_iw_output = parse_iw_scan


class WiFiScanner:
    """Run bounded ``iw`` scans with optional interface/RF-kill recovery hooks.

    ``retries`` is the number of retries after the initial attempt.  Hook
    callables receive the selected interface and should return ``False`` only
    when recovery definitely failed; ``None`` is accepted for mutating hooks.
    """

    def __init__(
        self,
        interface: str,
        *,
        retries: int = 2,
        retry_backoff: float = 0.5,
        timeout: float = 20.0,
        interface_is_up: Callable[[str], bool | None] | None = None,
        bring_interface_up: Callable[[str], bool | None] | None = None,
        unblock_rfkill: Callable[[str], bool | None] | None = None,
        command_runner: CommandRunner | None = None,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
        sleeper: Callable[[float], Any] = time.sleep,
    ) -> None:
        if not interface or not interface.strip():
            raise ValueError("interface is required")
        if retries < 0:
            raise ValueError("retries cannot be negative")
        if retry_backoff < 0:
            raise ValueError("retry_backoff cannot be negative")
        if timeout <= 0:
            raise ValueError("timeout must be positive")

        self.interface = interface.strip()
        self.retries = retries
        self.retry_backoff = retry_backoff
        self.timeout = timeout
        self.interface_is_up = interface_is_up
        self.bring_interface_up = bring_interface_up
        self.unblock_rfkill = unblock_rfkill
        if command_runner is not None and runner is not None:
            raise ValueError("pass command_runner or runner, not both")
        if command_runner is not None:
            self._command_runner = command_runner
        elif runner is None:
            self._command_runner = CommandRunner(default_timeout=timeout)
        else:
            self._command_runner = None
        self._runner = runner
        self._sleep = sleeper

    @staticmethod
    def _text(value: str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value

    def _prepare_interface(self) -> tuple[bool, str]:
        if self.interface_is_up is None:
            return True, ""
        try:
            interface_state = self.interface_is_up(self.interface)
            # ``None`` means the platform could not determine carrier/admin
            # state.  Let iw make the authoritative attempt in that case.
            if interface_state is not False:
                return True, ""
        except Exception as error:  # Hooks are platform integrations.
            return False, f"interface status hook failed: {error}"

        if self.bring_interface_up is None:
            return False, f"interface {self.interface!r} is down"
        try:
            recovered = self.bring_interface_up(self.interface)
        except Exception as error:  # Hooks are platform integrations.
            return False, f"interface recovery hook failed: {error}"
        if recovered is False:
            return False, f"could not bring interface {self.interface!r} up"
        return True, ""

    def _recover_rfkill(self, diagnostic: str) -> str:
        lowered = diagnostic.casefold()
        if "rf-kill" not in lowered and "rfkill" not in lowered:
            return diagnostic
        if self.unblock_rfkill is None:
            return diagnostic
        try:
            recovered = self.unblock_rfkill(self.interface)
            if recovered is False:
                return f"{diagnostic}; RF-kill recovery failed"
            if self.bring_interface_up is not None:
                brought_up = self.bring_interface_up(self.interface)
                if brought_up is False:
                    return f"{diagnostic}; interface remained down after RF-kill recovery"
        except Exception as error:  # Hooks are platform integrations.
            return f"{diagnostic}; RF-kill recovery hook failed: {error}"
        return diagnostic

    def _run_iw(self, command: list[str]) -> Any:
        if self._command_runner is not None:
            return self._command_runner.run(command, timeout=self.timeout, check=False)
        if self._runner is None:  # Defensive invariant; constructor sets one path.
            raise RuntimeError("scanner command runner is not configured")
        return self._runner(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=self.timeout,
        )

    def scan(self) -> list[AccessPoint]:
        """Return parsed access points or raise ``ScanError`` after retries."""

        attempts = self.retries + 1
        last_reason = "unknown scan failure"

        for attempt_index in range(attempts):
            prepared, preparation_error = self._prepare_interface()
            if not prepared:
                last_reason = preparation_error
            else:
                command = ["iw", "dev", self.interface, "scan"]
                try:
                    completed = self._run_iw(command)
                    stdout = self._text(completed.stdout)
                    stderr = self._text(completed.stderr)
                    command_failure = any(
                        line.strip().casefold().startswith("command failed:")
                        for line in stdout.splitlines()
                    )
                    if completed.returncode == 0 and not command_failure:
                        return parse_iw_scan(stdout)

                    diagnostic = (
                        stderr or stdout or f"iw exited with {completed.returncode}"
                    ).strip()
                    last_reason = self._recover_rfkill(diagnostic)
                except subprocess.TimeoutExpired:
                    last_reason = f"iw scan timed out after {self.timeout:g}s"
                except CommandTimeoutError:
                    last_reason = f"iw scan timed out after {self.timeout:g}s"
                except CommandError as error:
                    last_reason = str(error)
                except OSError as error:
                    last_reason = str(error)

            if attempt_index < attempts - 1 and self.retry_backoff:
                self._sleep(min(self.retry_backoff * (2**attempt_index), 30.0))

        raise ScanError(self.interface, attempts, last_reason)

    def scan_wps(self) -> list[AccessPoint]:
        """Run a scan and return only WPS-capable access points."""

        return [access_point for access_point in self.scan() if access_point.wps]


# Concise alias for newer integrations.
IwScanner = WiFiScanner
