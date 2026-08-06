"""Tests for wps_attack module."""

import socket
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

import pytest
from wifit_core.wps_attack import (
    PixieData,
    AttackProgress,
    WPASupplicantController,
    WPSAttackError,
)
from wifit_core.models import AttackMethod, AttackOutcome
from wifit_core.runner import CommandResult


# Skip controller tests on Windows (AF_UNIX not available)
skipif_windows = pytest.mark.skipif(
    sys.platform == "win32" or not hasattr(socket, "AF_UNIX"),
    reason="Unix domain sockets required (Linux/Termux only)",
)


def test_pixie_data_initialization():
    """Test PixieData initialization."""
    data = PixieData()
    assert data.pke == ""
    assert data.pkr == ""
    assert not data.is_complete()


def test_pixie_data_complete():
    """Test PixieData completeness check."""
    data = PixieData(
        pke="A" * 192,
        pkr="B" * 192,
        e_hash1="C" * 64,
        e_hash2="D" * 64,
        authkey="E" * 64,
        e_nonce="F" * 32,
    )
    assert data.is_complete()


def test_pixie_data_clear():
    """Test PixieData clear method."""
    data = PixieData(pke="test", pkr="test")
    data.clear()
    assert data.pke == ""
    assert data.pkr == ""


def test_attack_progress_initialization():
    """Test AttackProgress initialization."""
    progress = AttackProgress()
    assert progress.last_m_message == 0
    assert progress.essid == ""
    assert progress.attempts == 0
    assert not progress.first_half_valid()


def test_attack_progress_first_half_valid():
    """Test first half validity check."""
    progress = AttackProgress()
    progress.last_m_message = 5
    assert progress.first_half_valid()

    progress.last_m_message = 4
    assert not progress.first_half_valid()


def test_attack_progress_clear():
    """Test AttackProgress clear method."""
    progress = AttackProgress()
    progress.last_m_message = 5
    progress.essid = "TestNetwork"
    progress.clear()
    assert progress.last_m_message == 0
    assert progress.essid == ""


# ============================================================================
# WPASupplicantController Tests
# ============================================================================


@pytest.fixture
def mock_runner():
    """Create a mock CommandRunner."""
    runner = Mock()
    runner.run.return_value = CommandResult(
        argv=("wpa_supplicant",),
        returncode=0,
        stdout="",
        stderr="",
        duration_seconds=0.1,
    )
    return runner


@pytest.fixture
def mock_socket():
    """Create a mock socket that simulates wpa_supplicant responses."""
    sock = MagicMock()
    sock.recv.return_value = b"PONG\n"
    return sock


@skipif_windows
class TestControllerStartupExceptionSafety:
    """Test that controller startup failures properly cleanup resources."""

    def test_startup_failure_after_daemon_launch(self, mock_runner, tmp_path):
        """Test cleanup when control socket is not found after daemon launch."""
        mock_runner.run.return_value = CommandResult(
            argv=("wpa_supplicant",),
            returncode=0,
            stdout="",
            stderr="",
            duration_seconds=0.1,
        )

        ctrl = WPASupplicantController("wlan0", mock_runner)

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("shutil.rmtree") as mock_rmtree:
            with pytest.raises(WPSAttackError, match="control socket not found"):
                ctrl.start()

            # Verify cleanup was called
            mock_rmtree.assert_called_once()

    def test_startup_failure_on_socket_bind(self, mock_runner, tmp_path):
        """Test cleanup when socket bind fails."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        ctrl = WPASupplicantController("wlan0", mock_runner)

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls, patch(
            "shutil.rmtree"
        ) as mock_rmtree:
            mock_sock = MagicMock()
            mock_sock.bind.side_effect = OSError("Address already in use")
            mock_socket_cls.return_value = mock_sock

            with pytest.raises(WPSAttackError, match="Failed to bind client socket"):
                ctrl.start()

            # Verify cleanup was called
            mock_rmtree.assert_called_once()
            mock_sock.close.assert_called()

    def test_startup_failure_on_socket_connect(self, mock_runner, tmp_path):
        """Test cleanup when socket connect fails."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        ctrl = WPASupplicantController("wlan0", mock_runner)

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls, patch(
            "shutil.rmtree"
        ) as mock_rmtree:
            mock_sock = MagicMock()
            mock_sock.connect.side_effect = OSError("Connection refused")
            mock_socket_cls.return_value = mock_sock

            with pytest.raises(WPSAttackError, match="Failed to connect"):
                ctrl.start()

            # Verify cleanup was called
            mock_rmtree.assert_called_once()
            mock_sock.close.assert_called()

    def test_startup_failure_on_ping(self, mock_runner, tmp_path):
        """Test cleanup when PING command fails."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        ctrl = WPASupplicantController("wlan0", mock_runner)

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls, patch(
            "shutil.rmtree"
        ) as mock_rmtree:
            mock_sock = MagicMock()
            mock_sock.recv.return_value = b"FAIL\n"
            mock_socket_cls.return_value = mock_sock

            with pytest.raises(WPSAttackError, match="PING failed"):
                ctrl.start()

            # Verify cleanup was called
            mock_rmtree.assert_called_once()
            mock_sock.close.assert_called()

    def test_startup_failure_on_attach(self, mock_runner, tmp_path):
        """Test cleanup when ATTACH command fails."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        ctrl = WPASupplicantController("wlan0", mock_runner)

        responses = [b"PONG\n", b"FAIL\n"]

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls, patch(
            "shutil.rmtree"
        ) as mock_rmtree:
            mock_sock = MagicMock()
            mock_sock.recv.side_effect = responses
            mock_socket_cls.return_value = mock_sock

            with pytest.raises(WPSAttackError, match="ATTACH failed"):
                ctrl.start()

            # Verify cleanup was called
            mock_rmtree.assert_called_once()
            mock_sock.close.assert_called()


@skipif_windows
class TestControllerPINAttack:
    """Test PIN attack terminal paths."""

    def test_pin_command_rejected(self, mock_runner, tmp_path):
        """Test PIN attack when WPS_REG command is rejected."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        ctrl = WPASupplicantController("wlan0", mock_runner)

        responses = [b"PONG\n", b"OK\n", b"FAIL\n"]

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_sock.recv.side_effect = responses
            mock_socket_cls.return_value = mock_sock

            ctrl.start()

            result = ctrl.try_pin("AA:BB:CC:DD:EE:FF", "12345670", timeout=1.0)

            assert result.outcome == AttackOutcome.ERROR
            assert "rejected" in result.message
            assert result.method == AttackMethod.PIN

    def test_pin_success(self, mock_runner, tmp_path):
        """Test successful PIN attack."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        ctrl = WPASupplicantController("wlan0", mock_runner)

        startup_responses = [b"PONG\n", b"OK\n", b"OK\n"]
        event_responses = [
            b"WPS-CRED-RECEIVED\n",
            b"ssid='TestNetwork'\n",
            b"key='password123'\n",
        ]

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls, patch(
            "time.monotonic", side_effect=[0, 1, 2]
        ):
            mock_sock = MagicMock()
            mock_sock.recv.side_effect = startup_responses + event_responses
            mock_socket_cls.return_value = mock_sock

            ctrl.start()

            result = ctrl.try_pin("AA:BB:CC:DD:EE:FF", "12345670", timeout=30.0)

            assert result.outcome == AttackOutcome.SUCCESS
            assert result.method == AttackMethod.PIN
            assert result.wps_pin == "12345670"

    def test_pin_nack_first_half_valid(self, mock_runner, tmp_path):
        """Test PIN rejection with first half valid."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        ctrl = WPASupplicantController("wlan0", mock_runner)

        startup_responses = [b"PONG\n", b"OK\n", b"OK\n"]
        event_responses = [b"WPS M5 sent\n", b"WSC_NACK\n"]

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls, patch(
            "time.monotonic", side_effect=[0, 1, 2]
        ):
            mock_sock = MagicMock()
            mock_sock.recv.side_effect = startup_responses + event_responses
            mock_socket_cls.return_value = mock_sock

            ctrl.start()

            result = ctrl.try_pin("AA:BB:CC:DD:EE:FF", "12345670", timeout=30.0)

            assert result.outcome == AttackOutcome.FAILURE
            assert result.method == AttackMethod.PIN
            assert result.metadata.get("first_half_valid") is True

    def test_pin_nack_first_half_invalid(self, mock_runner, tmp_path):
        """Test PIN rejection with first half invalid."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        ctrl = WPASupplicantController("wlan0", mock_runner)

        startup_responses = [b"PONG\n", b"OK\n", b"OK\n"]
        event_responses = [b"WPS M3 sent\n", b"WSC_NACK\n"]

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls, patch(
            "time.monotonic", side_effect=[0, 1, 2]
        ):
            mock_sock = MagicMock()
            mock_sock.recv.side_effect = startup_responses + event_responses
            mock_socket_cls.return_value = mock_sock

            ctrl.start()

            result = ctrl.try_pin("AA:BB:CC:DD:EE:FF", "12345670", timeout=30.0)

            assert result.outcome == AttackOutcome.FAILURE
            assert result.method == AttackMethod.PIN
            assert "first_half_valid" not in result.metadata

    def test_pin_wps_fail(self, mock_runner, tmp_path):
        """Test PIN attack with WPS_FAIL."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        ctrl = WPASupplicantController("wlan0", mock_runner)

        startup_responses = [b"PONG\n", b"OK\n", b"OK\n"]
        event_responses = [b"WPS-FAIL\n"]

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls, patch(
            "time.monotonic", side_effect=[0, 1, 2]
        ):
            mock_sock = MagicMock()
            mock_sock.recv.side_effect = startup_responses + event_responses
            mock_socket_cls.return_value = mock_sock

            ctrl.start()

            result = ctrl.try_pin("AA:BB:CC:DD:EE:FF", "12345670", timeout=30.0)

            assert result.outcome == AttackOutcome.ERROR
            assert "transaction failed" in result.message
            assert result.method == AttackMethod.PIN

    def test_pin_timeout(self, mock_runner, tmp_path):
        """Test PIN attack timeout with monotonic clock."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        ctrl = WPASupplicantController("wlan0", mock_runner)

        startup_responses = [b"PONG\n", b"OK\n", b"OK\n"]

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls, patch(
            "time.monotonic", side_effect=[0, 1, 32]  # Start, check, timeout
        ):
            mock_sock = MagicMock()
            mock_sock.recv.side_effect = (
                startup_responses + [socket.timeout()] * 10
            )
            mock_socket_cls.return_value = mock_sock

            ctrl.start()

            result = ctrl.try_pin("AA:BB:CC:DD:EE:FF", "12345670", timeout=30.0)

            assert result.outcome == AttackOutcome.TIMEOUT
            assert "30s timeout" in result.message
            assert result.method == AttackMethod.PIN


@skipif_windows
class TestControllerNullPIN:
    """Test null PIN attack terminal paths."""

    def test_null_pin_command_rejected(self, mock_runner, tmp_path):
        """Test null PIN when WPS_REG command is rejected."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        ctrl = WPASupplicantController("wlan0", mock_runner)

        responses = [b"PONG\n", b"OK\n", b"FAIL\n"]

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_sock.recv.side_effect = responses
            mock_socket_cls.return_value = mock_sock

            ctrl.start()

            result = ctrl.try_null_pin("AA:BB:CC:DD:EE:FF", timeout=1.0)

            assert result.outcome == AttackOutcome.ERROR
            assert "rejected" in result.message
            assert result.method == AttackMethod.NULL_PIN

    def test_null_pin_success(self, mock_runner, tmp_path):
        """Test successful null PIN attack."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        ctrl = WPASupplicantController("wlan0", mock_runner)

        startup_responses = [b"PONG\n", b"OK\n", b"OK\n"]
        event_responses = [b"WPS-SUCCESS\n", b"ssid='TestNetwork'\n", b"key='pass'\n"]

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls, patch(
            "time.monotonic", side_effect=[0, 1, 2]
        ):
            mock_sock = MagicMock()
            mock_sock.recv.side_effect = startup_responses + event_responses
            mock_socket_cls.return_value = mock_sock

            ctrl.start()

            result = ctrl.try_null_pin("AA:BB:CC:DD:EE:FF", timeout=30.0)

            assert result.outcome == AttackOutcome.SUCCESS
            assert result.method == AttackMethod.NULL_PIN
            assert result.wps_pin == "(null)"

    def test_null_pin_timeout(self, mock_runner, tmp_path):
        """Test null PIN timeout."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        ctrl = WPASupplicantController("wlan0", mock_runner)

        startup_responses = [b"PONG\n", b"OK\n", b"OK\n"]

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls, patch(
            "time.monotonic", side_effect=[0, 1, 32]
        ):
            mock_sock = MagicMock()
            mock_sock.recv.side_effect = (
                startup_responses + [socket.timeout()] * 10
            )
            mock_socket_cls.return_value = mock_sock

            ctrl.start()

            result = ctrl.try_null_pin("AA:BB:CC:DD:EE:FF", timeout=30.0)

            assert result.outcome == AttackOutcome.TIMEOUT
            assert result.method == AttackMethod.NULL_PIN


@skipif_windows
class TestControllerPBC:
    """Test PBC attack terminal paths."""

    def test_pbc_command_rejected(self, mock_runner, tmp_path):
        """Test PBC when WPS_PBC command is rejected."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        ctrl = WPASupplicantController("wlan0", mock_runner)

        responses = [b"PONG\n", b"OK\n", b"FAIL\n"]

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_sock.recv.side_effect = responses
            mock_socket_cls.return_value = mock_sock

            ctrl.start()

            result = ctrl.try_pbc("AA:BB:CC:DD:EE:FF", timeout=1.0)

            assert result.outcome == AttackOutcome.ERROR
            assert "rejected" in result.message
            assert result.method == AttackMethod.PBC

    def test_pbc_targeted_success(self, mock_runner, tmp_path):
        """Test successful targeted PBC."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        ctrl = WPASupplicantController("wlan0", mock_runner)

        startup_responses = [b"PONG\n", b"OK\n", b"OK\n"]
        event_responses = [b"WPS-SUCCESS\n", b"ssid='TestAP'\n", b"key='password'\n"]

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls, patch(
            "time.monotonic", side_effect=[0, 1, 2]
        ):
            mock_sock = MagicMock()
            mock_sock.recv.side_effect = startup_responses + event_responses
            mock_socket_cls.return_value = mock_sock

            ctrl.start()

            result = ctrl.try_pbc("AA:BB:CC:DD:EE:FF", timeout=120.0)

            assert result.outcome == AttackOutcome.SUCCESS
            assert result.method == AttackMethod.PBC
            assert result.bssid == "aa:bb:cc:dd:ee:ff"

    def test_pbc_broadcast_success(self, mock_runner, tmp_path):
        """Test successful broadcast PBC."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        ctrl = WPASupplicantController("wlan0", mock_runner)

        startup_responses = [b"PONG\n", b"OK\n", b"OK\n"]
        event_responses = [b"WPS-SUCCESS\n", b"ssid='TestAP'\n", b"key='password'\n"]

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls, patch(
            "time.monotonic", side_effect=[0, 1, 2]
        ):
            mock_sock = MagicMock()
            mock_sock.recv.side_effect = startup_responses + event_responses
            mock_socket_cls.return_value = mock_sock

            ctrl.start()

            result = ctrl.try_pbc(None, timeout=120.0)

            assert result.outcome == AttackOutcome.SUCCESS
            assert result.method == AttackMethod.PBC
            assert result.bssid is None  # Broadcast preserves None

    def test_pbc_broadcast_bssid_preservation(self, mock_runner, tmp_path):
        """Test that broadcast PBC preserves None BSSID (not empty string)."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        ctrl = WPASupplicantController("wlan0", mock_runner)

        startup_responses = [b"PONG\n", b"OK\n", b"OK\n"]
        event_responses = [b"WPS-SUCCESS\n"]

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls, patch(
            "time.monotonic", side_effect=[0, 1, 2]
        ):
            mock_sock = MagicMock()
            mock_sock.recv.side_effect = startup_responses + event_responses
            mock_socket_cls.return_value = mock_sock

            ctrl.start()

            result = ctrl.try_pbc(None, timeout=120.0)

            # Critical: BSSID must be None, not ""
            assert result.bssid is None
            assert result.bssid != ""

    def test_pbc_timeout(self, mock_runner, tmp_path):
        """Test PBC timeout (no button press)."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        ctrl = WPASupplicantController("wlan0", mock_runner)

        startup_responses = [b"PONG\n", b"OK\n", b"OK\n"]

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls, patch(
            "time.monotonic", side_effect=[0, 1, 122]
        ):
            mock_sock = MagicMock()
            mock_sock.recv.side_effect = (
                startup_responses + [socket.timeout()] * 10
            )
            mock_socket_cls.return_value = mock_sock

            ctrl.start()

            result = ctrl.try_pbc("AA:BB:CC:DD:EE:FF", timeout=120.0)

            assert result.outcome == AttackOutcome.TIMEOUT
            assert "120s" in result.message
            assert result.method == AttackMethod.PBC

    def test_pbc_failure(self, mock_runner, tmp_path):
        """Test PBC failure."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        ctrl = WPASupplicantController("wlan0", mock_runner)

        startup_responses = [b"PONG\n", b"OK\n", b"OK\n"]
        event_responses = [b"WPS-FAIL\n"]

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls, patch(
            "time.monotonic", side_effect=[0, 1, 2]
        ):
            mock_sock = MagicMock()
            mock_sock.recv.side_effect = startup_responses + event_responses
            mock_socket_cls.return_value = mock_sock

            ctrl.start()

            result = ctrl.try_pbc("AA:BB:CC:DD:EE:FF", timeout=120.0)

            assert result.outcome == AttackOutcome.FAILURE
            assert "failed or rejected" in result.message
            assert result.method == AttackMethod.PBC


@skipif_windows
class TestControllerCleanup:
    """Test controller cleanup verification."""

    def test_cleanup_on_context_exit(self, mock_runner, tmp_path):
        """Test cleanup is called when exiting context manager."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        responses = [b"PONG\n", b"OK\n"]

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls, patch(
            "shutil.rmtree"
        ) as mock_rmtree:
            mock_sock = MagicMock()
            mock_sock.recv.side_effect = responses
            mock_socket_cls.return_value = mock_sock

            with WPASupplicantController("wlan0", mock_runner) as ctrl:
                pass

            # Verify cleanup
            mock_sock.close.assert_called()
            mock_rmtree.assert_called_once()

    def test_wps_cancel_called_on_success(self, mock_runner, tmp_path):
        """Test WPS_CANCEL is sent after successful attack."""
        ctrl_socket = tmp_path / "wlan0"
        ctrl_socket.touch()

        ctrl = WPASupplicantController("wlan0", mock_runner)

        startup_responses = [b"PONG\n", b"OK\n", b"OK\n"]
        event_responses = [b"WPS-SUCCESS\n"]

        with patch("tempfile.mkdtemp", return_value=str(tmp_path)), patch(
            "time.sleep"
        ), patch("socket.socket") as mock_socket_cls, patch(
            "time.monotonic", side_effect=[0, 1, 2]
        ):
            mock_sock = MagicMock()
            mock_sock.recv.side_effect = startup_responses + event_responses
            mock_sock.send = MagicMock()
            mock_socket_cls.return_value = mock_sock

            ctrl.start()
            ctrl.try_pin("AA:BB:CC:DD:EE:FF", "12345670", timeout=30.0)

            # Verify WPS_CANCEL was sent
            cancel_calls = [
                call for call in mock_sock.send.call_args_list if b"WPS_CANCEL" in call[0][0]
            ]
            assert len(cancel_calls) >= 1
