import subprocess
import unittest
from unittest import mock

from wifit_core.models import SecurityMode, WPSVersion, WPSVersionEvidence
from wifit_core.scanner import ScanError, WiFiScanner, parse_iw_scan


IW_SCAN_OUTPUT = r"""
BSS aa:bb:cc:dd:ee:01(on wlan-test.0)
	freq: 2412
	signal: -35.50 dBm
	SSID: Cafe\x20WiFi
	capability: ESS Privacy ShortSlotTime (0x0411)
	RSN:     * Version: 1
		* Group cipher: CCMP
		* Pairwise ciphers: CCMP
		* Authentication suites: PSK SAE
	WPS:     * Version: 1.0
		* Wi-Fi Protected Setup State: 2 (Configured)
		* AP setup locked: 0x00
		* Manufacturer: Acme\x20Corp
		* Model: Router Pro
		* Model Number: RP-200
		* Device name: Acme\x20Gateway
		* Version2: 2.0
BSS AA:BB:CC:DD:EE:02 (on wlan-test.0)
	freq: 5180
	signal: -70 dBm
	SSID: Secure 6
	capability: ESS Privacy (0x0011)
	RSN:     * Version: 1
		* Authentication suites: SAE
	WPS:     * Version: 1.0
		* AP setup locked: 0x0A
		* Model: LegacyBox
BSS aa:bb:cc:dd:ee:03 (on wlan-test.0)
	freq: 5935
	SSID:
	capability: ESS (0x0001)
"""


class IwParserTests(unittest.TestCase):
    def test_parses_wps_wpa3_lock_and_wsc_fields(self):
        access_points = parse_iw_scan(IW_SCAN_OUTPUT)

        self.assertEqual(len(access_points), 3)
        transition = access_points[0]
        self.assertEqual(transition.bssid, "AA:BB:CC:DD:EE:01")
        self.assertEqual(transition.ssid, "Cafe WiFi")
        self.assertEqual(transition.signal_dbm, -35.5)
        self.assertEqual(transition.channel, 1)
        self.assertEqual(transition.security, SecurityMode.WPA2_WPA3)
        self.assertTrue(transition.wpa3)
        self.assertTrue(transition.wpa3_transition)
        self.assertEqual(transition.wps_version, WPSVersion.VERSION_2)
        self.assertEqual(transition.wps_version_evidence, WPSVersionEvidence.CONFIRMED)
        self.assertFalse(transition.wps_locked)
        self.assertEqual(transition.wsc_manufacturer, "Acme Corp")
        self.assertEqual(transition.wsc_model_name, "Router Pro")
        self.assertEqual(transition.wsc_model_number, "RP-200")
        self.assertEqual(transition.wsc_device_name, "Acme Gateway")

        sae_only = access_points[1]
        self.assertEqual(sae_only.security, SecurityMode.WPA3)
        self.assertTrue(sae_only.wpa3)
        self.assertFalse(sae_only.wpa3_transition)
        self.assertEqual(sae_only.wps_version, WPSVersion.VERSION_1)
        self.assertEqual(sae_only.wps_version_evidence, WPSVersionEvidence.INFERRED)
        self.assertTrue(sae_only.wps_locked)
        self.assertEqual(sae_only.channel, 36)

        hidden = access_points[2]
        self.assertEqual(hidden.ssid, "<hidden>")
        self.assertEqual(hidden.security, SecurityMode.OPEN)
        self.assertFalse(hidden.wps)
        self.assertIsNone(hidden.wps_version)
        self.assertIsNone(hidden.wps_locked)
        self.assertEqual(hidden.channel, 2)

    def test_distinguishes_explicit_wps_one_from_inference(self):
        output = """
BSS 00:11:22:33:44:55 (on wlan0)
    freq: 2462
    signal: -40 dBm
    SSID: Explicit
    WPS: * Version: 1.0
        * Version2: 1.0
        * AP setup locked: false
"""
        access_point = parse_iw_scan(output)[0]

        self.assertEqual(access_point.wps_version, WPSVersion.VERSION_1)
        self.assertEqual(access_point.wps_version_evidence, WPSVersionEvidence.CONFIRMED)
        self.assertFalse(access_point.wps_locked)


class IwScannerRetryTests(unittest.TestCase):
    def test_accepts_unified_command_runner(self):
        command_runner = mock.Mock()
        command_runner.run.return_value = subprocess.CompletedProcess(
            ["iw"], 0, stdout=IW_SCAN_OUTPUT, stderr=""
        )
        scanner = WiFiScanner(
            "wlan0",
            retries=0,
            timeout=7.5,
            command_runner=command_runner,
            interface_is_up=lambda _interface: None,
        )

        self.assertEqual(len(scanner.scan()), 3)
        command_runner.run.assert_called_once_with(
            ["iw", "dev", "wlan0", "scan"], timeout=7.5, check=False
        )

    def test_recovers_rfkill_then_retries_with_backoff(self):
        calls = []
        recoveries = []
        sleeps = []

        def runner(command, **_kwargs):
            calls.append(command)
            if len(calls) == 1:
                return subprocess.CompletedProcess(
                    command,
                    1,
                    stdout="",
                    stderr="command failed: Operation not possible due to RF-kill (-132)",
                )
            return subprocess.CompletedProcess(command, 0, stdout=IW_SCAN_OUTPUT, stderr="")

        scanner = WiFiScanner(
            "wlan0",
            retries=1,
            retry_backoff=0.25,
            interface_is_up=lambda _interface: True,
            bring_interface_up=lambda interface: recoveries.append(("up", interface)),
            unblock_rfkill=lambda interface: recoveries.append(("rfkill", interface)),
            runner=runner,
            sleeper=sleeps.append,
        )

        self.assertEqual(len(scanner.scan()), 3)
        self.assertEqual(len(calls), 2)
        self.assertEqual(recoveries, [("rfkill", "wlan0"), ("up", "wlan0")])
        self.assertEqual(sleeps, [0.25])

    def test_brings_down_interface_up_before_scan(self):
        brought_up = []

        scanner = WiFiScanner(
            "wlan0",
            retries=0,
            interface_is_up=lambda _interface: False,
            bring_interface_up=lambda interface: brought_up.append(interface),
            runner=lambda command, **_kwargs: subprocess.CompletedProcess(
                command, 0, stdout=IW_SCAN_OUTPUT, stderr=""
            ),
        )

        self.assertEqual(len(scanner.scan_wps()), 2)
        self.assertEqual(brought_up, ["wlan0"])

    def test_failure_is_bounded_and_reports_attempt_count(self):
        calls = []
        sleeps = []

        def runner(command, **_kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(
                command, 16, stdout="", stderr="Device or resource busy"
            )

        scanner = WiFiScanner(
            "wlan0",
            retries=2,
            retry_backoff=0.1,
            runner=runner,
            sleeper=sleeps.append,
        )

        with self.assertRaises(ScanError) as raised:
            scanner.scan()

        self.assertEqual(raised.exception.attempts, 3)
        self.assertIn("Device or resource busy", str(raised.exception))
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleeps, [0.1, 0.2])


if __name__ == "__main__":
    unittest.main()
