"""Typed records shared by WiFiT scanners, attacks, and reporters."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

_BSSID_RE = re.compile(r"^[0-9A-F]{12}$")


def normalize_bssid(value: str) -> str:
    """Return a canonical upper-case BSSID or raise ``ValueError``."""

    normalized = re.sub(r"[:.\-]", "", value.strip()).upper()
    if not _BSSID_RE.fullmatch(normalized):
        raise ValueError(f"Invalid BSSID: {value!r}")
    return ":".join(normalized[index : index + 2] for index in range(0, 12, 2))


class WPSVersion(str, Enum):
    """WPS protocol generation reported or inferred from scan data."""

    UNKNOWN = "unknown"
    VERSION_1 = "1.0"
    VERSION_2 = "2.0"


class WPSVersionEvidence(str, Enum):
    """How confidently a WPS version was identified."""

    UNKNOWN = "unknown"
    INFERRED = "inferred"
    CONFIRMED = "confirmed"


class SecurityMode(str, Enum):
    """Normalized Wi-Fi security modes exposed by the scanner."""

    OPEN = "Open"
    WEP = "WEP"
    WPA = "WPA"
    WPA2 = "WPA2"
    WPA3 = "WPA3"
    WPA_WPA2 = "WPA/WPA2"
    WPA2_WPA3 = "WPA2/WPA3"
    UNKNOWN = "Unknown"


class AttackMethod(str, Enum):
    """Supported connection, attack, and offline-generation methods."""

    PIN = "pin"
    NULL_PIN = "null-pin"
    ZERO_PIN = "zero-pin"
    EMPTY_PIN = "empty-pin"
    PBC = "pbc"
    PIXIE_DUST = "pixie-dust"
    ONLINE_BRUTEFORCE = "online-bruteforce"
    OFFLINE_PIN_GENERATION = "offline-pin-generation"


class AttackOutcome(str, Enum):
    """Terminal outcomes suitable for both UI display and reporting."""

    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"
    CANCELLED = "cancelled"
    LOCKED = "locked"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass(slots=True)
class AccessPoint:
    """A normalized access point parsed from an ``iw`` BSS block.

    ``wps_locked`` is deliberately tri-state: ``True`` means the AP explicitly
    reports a lock, ``False`` means it explicitly reports no lock, and ``None``
    means the scan did not provide a lock attribute.
    """

    bssid: str
    ssid: str = "<hidden>"
    signal_dbm: float | None = None
    channel: int | None = None
    frequency_mhz: int | None = None
    wps: bool = False
    wps_version: WPSVersion | None = None
    wps_version_evidence: WPSVersionEvidence = WPSVersionEvidence.UNKNOWN
    wps_locked: bool | None = None
    security: SecurityMode = SecurityMode.UNKNOWN
    wpa3: bool = False
    wpa3_transition: bool = False
    wsc_manufacturer: str = ""
    wsc_model_name: str = ""
    wsc_model_number: str = ""
    wsc_device_name: str = ""
    vulnerability_reasons: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.bssid = normalize_bssid(self.bssid)
        self.ssid = self.ssid or "<hidden>"
        if not isinstance(self.security, SecurityMode):
            self.security = SecurityMode(self.security)
        if self.wps_version is not None and not isinstance(self.wps_version, WPSVersion):
            self.wps_version = WPSVersion(self.wps_version)
        if not isinstance(self.wps_version_evidence, WPSVersionEvidence):
            self.wps_version_evidence = WPSVersionEvidence(self.wps_version_evidence)
        if self.wps_version is not None:
            self.wps = True
        if self.security is SecurityMode.WPA2_WPA3:
            self.wpa3_transition = True
        if self.security in {SecurityMode.WPA3, SecurityMode.WPA2_WPA3}:
            self.wpa3 = True

    @property
    def model(self) -> str:
        """Compatibility alias for the WSC model name."""

        return self.wsc_model_name

    @property
    def model_number(self) -> str:
        """Compatibility alias for the WSC model number."""

        return self.wsc_model_number

    @property
    def device_name(self) -> str:
        """Compatibility alias for the WSC device name."""

        return self.wsc_device_name

    def to_record(self) -> dict[str, Any]:
        """Return a JSON/CSV-friendly record without enum instances."""

        return {
            "bssid": self.bssid,
            "ssid": self.ssid,
            "signal_dbm": self.signal_dbm,
            "channel": self.channel,
            "frequency_mhz": self.frequency_mhz,
            "wps": self.wps,
            "wps_version": self.wps_version.value if self.wps_version else None,
            "wps_version_evidence": self.wps_version_evidence.value,
            "wps_locked": self.wps_locked,
            "security": self.security.value,
            "wpa3": self.wpa3,
            "wpa3_transition": self.wpa3_transition,
            "wsc_manufacturer": self.wsc_manufacturer,
            "wsc_model_name": self.wsc_model_name,
            "wsc_model_number": self.wsc_model_number,
            "wsc_device_name": self.wsc_device_name,
            "vulnerability_reasons": list(self.vulnerability_reasons),
        }


@dataclass(slots=True)
class AttackResult:
    """A terminal result from an online or offline WPS operation."""

    method: AttackMethod
    outcome: AttackOutcome
    bssid: str | None = None
    ssid: str | None = None
    interface: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    wps_pin: str | None = None
    network_key: str | None = None
    attempts: int | None = None
    message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.method, AttackMethod):
            self.method = AttackMethod(self.method)
        if not isinstance(self.outcome, AttackOutcome):
            self.outcome = AttackOutcome(self.outcome)
        if self.bssid:
            self.bssid = normalize_bssid(self.bssid)
        if self.attempts is not None and self.attempts < 0:
            raise ValueError("attempts cannot be negative")
        if self.finished_at:
            start_is_aware = self.started_at.utcoffset() is not None
            finish_is_aware = self.finished_at.utcoffset() is not None
            if start_is_aware != finish_is_aware:
                raise ValueError("started_at and finished_at must use matching timezones")
            if self.finished_at < self.started_at:
                raise ValueError("finished_at cannot precede started_at")

    @property
    def successful(self) -> bool:
        return self.outcome is AttackOutcome.SUCCESS

    @property
    def duration_seconds(self) -> float | None:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    @property
    def contains_credentials(self) -> bool:
        return self.wps_pin is not None or self.network_key is not None

    @property
    def pin(self) -> str | None:
        """Compatibility alias for callers that use ``pin``."""

        return self.wps_pin

    @property
    def psk(self) -> str | None:
        """Compatibility alias for callers that use ``psk``."""

        return self.network_key

    def to_record(self) -> dict[str, Any]:
        """Return a JSON/CSV-friendly record without enum instances."""

        return {
            "method": self.method.value,
            "outcome": self.outcome.value,
            "bssid": self.bssid,
            "ssid": self.ssid,
            "interface": self.interface,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "wps_pin": self.wps_pin,
            "network_key": self.network_key,
            "attempts": self.attempts,
            "message": self.message,
            "metadata": dict(self.metadata),
        }
