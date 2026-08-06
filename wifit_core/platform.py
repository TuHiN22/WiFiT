"""Wireless-interface and radio state handling.

All changes made by :class:`PlatformManager` are recorded and reversed when
the manager leaves its context.  The implementation deliberately treats
missing Android and rfkill utilities as optional capabilities.
"""

from __future__ import annotations

import os
import re
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .runner import CommandError, CommandResult, CommandRunner

_INTERFACE_NAME = re.compile(r"^[A-Za-z0-9_.:-]{1,15}$")
_RFKILL_HEADER = re.compile(r"^(\d+):\s*([^:]+):\s*(.+?)\s*$")


class PlatformError(RuntimeError):
    """The host could not provide or prepare a wireless interface."""


@dataclass(frozen=True, slots=True)
class WirelessInterface:
    name: str
    phy: str | None = None
    ifindex: int | None = None
    wdev: str | None = None
    address: str | None = None
    interface_type: str | None = None
    channel: int | None = None
    frequency_mhz: int | None = None
    txpower_dbm: float | None = None


@dataclass(frozen=True, slots=True)
class RfkillState:
    identifier: str
    device: str
    kind: str
    soft_blocked: bool
    hard_blocked: bool

    @property
    def is_wifi(self) -> bool:
        kind = self.kind.casefold()
        device = self.device.casefold()
        return (
            "wireless" in kind
            or "wlan" in kind
            or "wifi" in kind
            or device.startswith("phy")
            or device.startswith("wlan")
        )


@dataclass(frozen=True, slots=True)
class AndroidWifiState:
    wifi_on: bool | None
    scan_always_enabled: bool | None


def parse_iw_dev(output: str) -> tuple[WirelessInterface, ...]:
    """Parse ``iw dev`` output without depending on indentation widths."""

    interfaces: list[WirelessInterface] = []
    current_phy: str | None = None
    current: dict[str, object] | None = None

    def finish() -> None:
        nonlocal current
        if current is not None:
            # Type ignore: dict is validated to have correct structure
            interfaces.append(WirelessInterface(**current))  # type: ignore[arg-type]
            current = None

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        phy_match = re.fullmatch(r"phy#(\d+)", line)
        if phy_match:
            finish()
            current_phy = f"phy#{phy_match.group(1)}"
            continue
        interface_match = re.fullmatch(r"Interface\s+(\S+)", line)
        if interface_match:
            finish()
            current = {"name": interface_match.group(1), "phy": current_phy}
            continue
        if current is None:
            continue

        key, separator, value = line.partition(" ")
        value = value.strip() if separator else ""
        if key == "ifindex" and value.isdigit():
            current["ifindex"] = int(value)
        elif key == "wdev" and value:
            current["wdev"] = value.split()[0]
        elif key == "addr" and value:
            current["address"] = value.split()[0].upper()
        elif key == "type" and value:
            current["interface_type"] = value
        elif key == "channel":
            channel_match = re.match(r"(\d+)\s+\((\d+)\s+MHz\)", value)
            if channel_match:
                current["channel"] = int(channel_match.group(1))
                current["frequency_mhz"] = int(channel_match.group(2))
        elif key == "txpower":
            power_match = re.match(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))", value)
            if power_match:
                current["txpower_dbm"] = float(power_match.group(1))

    finish()
    return tuple(interfaces)


def parse_rfkill_list(output: str) -> tuple[RfkillState, ...]:
    """Parse the stable, human-readable output of ``rfkill list``."""

    states: list[RfkillState] = []
    current: dict[str, object] | None = None

    def finish() -> None:
        nonlocal current
        if current is not None:
            states.append(
                RfkillState(
                    identifier=str(current["identifier"]),
                    device=str(current["device"]),
                    kind=str(current["kind"]),
                    soft_blocked=bool(current.get("soft_blocked", False)),
                    hard_blocked=bool(current.get("hard_blocked", False)),
                )
            )
            current = None

    for raw_line in output.splitlines():
        line = raw_line.strip()
        header = _RFKILL_HEADER.match(line)
        if header:
            finish()
            current = {
                "identifier": header.group(1),
                "device": header.group(2).strip(),
                "kind": header.group(3).strip(),
            }
            continue
        if current is None:
            continue
        key, separator, value = line.partition(":")
        if not separator:
            continue
        blocked = value.strip().casefold() in {"yes", "1", "true", "blocked"}
        normalised_key = key.strip().casefold()
        if normalised_key == "soft blocked":
            current["soft_blocked"] = blocked
        elif normalised_key == "hard blocked":
            current["hard_blocked"] = blocked

    finish()
    return tuple(states)


def parse_link_is_up(output: str) -> bool | None:
    """Return the administrative UP flag from ``ip link`` output."""

    flags_match = re.search(r"<([^>]+)>", output)
    if flags_match:
        flags = {flag.strip().upper() for flag in flags_match.group(1).split(",")}
        return "UP" in flags
    state_match = re.search(r"\bstate\s+(UP|DOWN|UNKNOWN)\b", output, re.I)
    if state_match and state_match.group(1).upper() != "UNKNOWN":
        return state_match.group(1).upper() == "UP"
    return None


class PlatformManager:
    """Prepare one wireless interface and restore the prior radio state."""

    def __init__(
        self,
        interface: str | None = None,
        *,
        runner: CommandRunner | None = None,
        is_android: bool | None = None,
        sys_class_net: str | os.PathLike[str] = "/sys/class/net",
        poll_attempts: int = 5,
        poll_interval: float = 0.2,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if poll_attempts < 1:
            raise ValueError("poll_attempts must be at least one")
        if poll_interval < 0:
            raise ValueError("poll_interval may not be negative")
        if interface is not None:
            self._validate_interface(interface)

        self.requested_interface = interface
        self.runner = runner or CommandRunner()
        self.is_android = self._detect_android() if is_android is None else is_android
        self.sys_class_net = Path(sys_class_net)
        self.poll_attempts = poll_attempts
        self.poll_interval = poll_interval
        self._sleep = sleep

        self.interface: str | None = None
        self._prepared = False
        self._original_interface_up: bool | None = None
        self._interface_changed = False
        self._rfkill_snapshot: tuple[RfkillState, ...] = ()
        self._unblocked_rfkill_ids: set[str] = set()
        self._android_snapshot = AndroidWifiState(None, None)
        self._android_wifi_changed = False
        self._android_scan_changed = False

    @staticmethod
    def _detect_android() -> bool:
        return bool(
            os.environ.get("ANDROID_ROOT")
            or os.environ.get("ANDROID_DATA")
            or Path("/system/build.prop").is_file()
        )

    @staticmethod
    def _validate_interface(interface: str) -> None:
        if not _INTERFACE_NAME.fullmatch(interface):
            raise ValueError(f"invalid wireless interface name: {interface!r}")

    def list_interfaces(self) -> tuple[WirelessInterface, ...]:
        result = self._optional_run(("iw", "dev"), timeout=10.0)
        if result is None or not result.ok:
            return ()
        return parse_iw_dev(result.stdout)

    def interface_is_up(self, interface: str) -> bool | None:
        self._validate_interface(interface)
        result = self._optional_run(("ip", "-o", "link", "show", "dev", interface), timeout=5.0)
        if result is not None and result.ok:
            parsed = parse_link_is_up(result.stdout)
            if parsed is not None:
                return parsed

        # sysfs remains available on stripped-down Android builds where the
        # ip utility is absent or has a reduced feature set.
        try:
            flags = int(
                (self.sys_class_net / interface / "flags").read_text(encoding="ascii").strip(),
                0,
            )
        except (OSError, ValueError):
            return None
        return bool(flags & 0x1)  # Linux IFF_UP

    def select_interface(
        self,
        interface: str | None = None,
        *,
        bring_up: bool = True,
        candidates: Iterable[WirelessInterface] | None = None,
    ) -> str:
        preferred = interface or self.requested_interface
        if preferred is not None:
            self._validate_interface(preferred)

        available = tuple(candidates) if candidates is not None else self.list_interfaces()
        if not available:
            raise PlatformError("iw did not report a wireless interface")

        up_states = {item.name: self.interface_is_up(item.name) for item in available}
        if preferred is not None:
            selected = next((item for item in available if item.name == preferred), None)
            if selected is None:
                names = ", ".join(item.name for item in available)
                raise PlatformError(
                    f"wireless interface {preferred!r} was not found"
                    + (f" (available: {names})" if names else "")
                )
        else:
            # Prefer an already-up managed station.  Stable input ordering is
            # the final tie breaker, matching iw's deterministic output.
            def score(item: WirelessInterface) -> tuple[int, int, int]:
                kind = (item.interface_type or "").casefold()
                return (
                    1 if kind in {"managed", "station"} else 0,
                    1 if up_states[item.name] is True else 0,
                    1 if item.name.startswith(("wlan", "wlp", "wlo")) else 0,
                )

            selected = max(available, key=score)

        self.interface = selected.name
        self._original_interface_up = up_states[selected.name]
        if bring_up and self._original_interface_up is not True:
            result = self._optional_run(
                ("ip", "link", "set", "dev", selected.name, "up"), timeout=8.0
            )
            if result is None or not result.ok:
                detail = result.stderr.strip() if result is not None else "ip is unavailable"
                raise PlatformError(f"could not bring interface {selected.name!r} up: {detail}")
            # Only restore DOWN when it was positively observed before our
            # change; an unknown original state must not be guessed at exit.
            self._interface_changed = self._original_interface_up is False
        return selected.name

    def snapshot_rfkill(self) -> tuple[RfkillState, ...]:
        result = self._optional_run(("rfkill", "list"), timeout=5.0)
        if result is None or not result.ok:
            return ()
        return parse_rfkill_list(result.stdout)

    def unblock_wifi(self, snapshot: Sequence[RfkillState] | None = None) -> tuple[str, ...]:
        states = tuple(snapshot) if snapshot is not None else self.snapshot_rfkill()
        changed: list[str] = []
        for state in states:
            if not state.is_wifi or not state.soft_blocked or state.hard_blocked:
                continue
            result = self._optional_run(("rfkill", "unblock", state.identifier), timeout=5.0)
            if result is not None and result.ok:
                self._unblocked_rfkill_ids.add(state.identifier)
                changed.append(state.identifier)
        return tuple(changed)

    def snapshot_android_wifi(self) -> AndroidWifiState:
        if not self.is_android:
            return AndroidWifiState(None, None)
        return AndroidWifiState(
            wifi_on=self._get_android_boolean("wifi_on"),
            scan_always_enabled=self._get_android_boolean("wifi_scan_always_enabled"),
        )

    def prepare(
        self,
        *,
        disable_android_always_scan: bool = True,
        enable_android_wifi: bool = True,
    ) -> str:
        """Prepare and return a wireless interface exactly once."""

        if self._prepared:
            if self.interface is None:  # Defensive invariant guard.
                raise PlatformError("platform preparation did not select an interface")
            return self.interface

        self._prepared = True
        try:
            self._android_snapshot = self.snapshot_android_wifi()
            self._rfkill_snapshot = self.snapshot_rfkill()
            self.unblock_wifi(self._rfkill_snapshot)

            if (
                self.is_android
                and disable_android_always_scan
                and self._android_snapshot.scan_always_enabled is True
            ):
                self._android_scan_changed = self._put_android_boolean(
                    "wifi_scan_always_enabled", False
                )

            if self.is_android and enable_android_wifi and self._android_snapshot.wifi_on is False:
                self._android_wifi_changed = self._set_android_wifi(True)

            interfaces: tuple[WirelessInterface, ...] = ()
            for attempt in range(self.poll_attempts):
                interfaces = self.list_interfaces()
                if interfaces:
                    break
                if attempt + 1 < self.poll_attempts:
                    self._sleep(self.poll_interval)

            return self.select_interface(candidates=interfaces)
        except Exception:
            self.restore()
            raise

    def restore(self) -> tuple[str, ...]:
        """Best-effort restoration; repeated calls are harmless."""

        if not self._prepared:
            return ()
        failures: list[str] = []

        if self._interface_changed and self.interface is not None:
            result = self._optional_run(
                ("ip", "link", "set", "dev", self.interface, "down"), timeout=8.0
            )
            if result is None or not result.ok:
                failures.append(f"failed to restore {self.interface} to DOWN")
            else:
                self._interface_changed = False

        rfkill_failures: set[str] = set()
        for identifier in sorted(self._unblocked_rfkill_ids):
            result = self._optional_run(("rfkill", "block", identifier), timeout=5.0)
            if result is None or not result.ok:
                failures.append(f"failed to restore rfkill {identifier}")
                rfkill_failures.add(identifier)
        self._unblocked_rfkill_ids = rfkill_failures

        if self._android_scan_changed:
            original = self._android_snapshot.scan_always_enabled
            if original is not None and not self._put_android_boolean(
                "wifi_scan_always_enabled", original
            ):
                failures.append("failed to restore Android always-scan setting")
            else:
                self._android_scan_changed = False

        if self._android_wifi_changed:
            original_wifi = self._android_snapshot.wifi_on
            if original_wifi is not None and not self._set_android_wifi(original_wifi):
                failures.append("failed to restore Android Wi-Fi setting")
            else:
                self._android_wifi_changed = False

        # Keep only failed restoration work active so a later call can retry
        # it without replaying changes that have already been reversed.
        self._prepared = bool(
            self._interface_changed
            or self._unblocked_rfkill_ids
            or self._android_wifi_changed
            or self._android_scan_changed
        )
        return tuple(failures)

    def _get_android_boolean(self, key: str) -> bool | None:
        result = self._optional_run(("settings", "get", "global", key), timeout=5.0)
        if result is None or not result.ok:
            return None
        value = result.stdout.strip().casefold()
        if value in {"1", "true", "enabled", "on"}:
            return True
        if value in {"0", "false", "disabled", "off"}:
            return False
        return None

    def _put_android_boolean(self, key: str, enabled: bool) -> bool:
        result = self._optional_run(
            ("settings", "put", "global", key, "1" if enabled else "0"),
            timeout=5.0,
        )
        return result is not None and result.ok

    def _set_android_wifi(self, enabled: bool) -> bool:
        state = "enable" if enabled else "disable"
        result = self._optional_run(("svc", "wifi", state), timeout=10.0)
        if result is not None and result.ok:
            return True
        modern_state = "enabled" if enabled else "disabled"
        result = self._optional_run(("cmd", "wifi", "set-wifi-enabled", modern_state), timeout=10.0)
        return result is not None and result.ok

    def _optional_run(self, argv: Sequence[str], *, timeout: float) -> CommandResult | None:
        try:
            return self.runner.run(argv, timeout=timeout)
        except CommandError:
            return None

    def __enter__(self) -> PlatformManager:
        self.prepare()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.restore()


WirelessPlatform = PlatformManager


__all__ = [
    "AndroidWifiState",
    "PlatformError",
    "PlatformManager",
    "RfkillState",
    "WirelessInterface",
    "WirelessPlatform",
    "parse_iw_dev",
    "parse_link_is_up",
    "parse_rfkill_list",
]
