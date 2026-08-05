import unittest

from wifit_core.platform import (
    PlatformError,
    PlatformManager,
    parse_iw_dev,
    parse_link_is_up,
    parse_rfkill_list,
)
from wifit_core.runner import CommandResult


def result(argv, stdout="", stderr="", returncode=0):
    return CommandResult(tuple(argv), returncode, stdout, stderr, 0.01)


class FakeRunner:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    def run(self, argv, *, timeout=None, **kwargs):
        key = tuple(argv)
        self.calls.append((key, timeout))
        response = self.responses.get(key)
        if callable(response):
            return response(key)
        if response is not None:
            return response
        return result(key)


IW_OUTPUT = """\
phy#0
\tInterface p2p0
\t\tifindex 5
\t\taddr 02:11:22:33:44:55
\t\ttype P2P-device
\tInterface wlan0
\t\tifindex 4
\t\twdev 0x1
\t\taddr aa:bb:cc:dd:ee:ff
\t\ttype managed
\t\tchannel 6 (2437 MHz), width: 20 MHz, center1: 2437 MHz
\t\ttxpower 20.00 dBm
phy#1
\tInterface wlan1
\t\tifindex 7
\t\ttype managed
"""


class PlatformParserTests(unittest.TestCase):
    def test_parse_iw_dev_keeps_interface_metadata(self):
        interfaces = parse_iw_dev(IW_OUTPUT)

        self.assertEqual([item.name for item in interfaces], ["p2p0", "wlan0", "wlan1"])
        wlan0 = interfaces[1]
        self.assertEqual(wlan0.phy, "phy#0")
        self.assertEqual(wlan0.address, "AA:BB:CC:DD:EE:FF")
        self.assertEqual(wlan0.channel, 6)
        self.assertEqual(wlan0.frequency_mhz, 2437)
        self.assertEqual(wlan0.txpower_dbm, 20.0)

    def test_parse_rfkill_list_tracks_soft_and_hard_blocks(self):
        states = parse_rfkill_list(
            """0: phy0: Wireless LAN
\tSoft blocked: yes
\tHard blocked: no
1: hci0: Bluetooth
\tSoft blocked: no
\tHard blocked: yes
"""
        )

        self.assertEqual(len(states), 2)
        self.assertTrue(states[0].is_wifi)
        self.assertTrue(states[0].soft_blocked)
        self.assertFalse(states[0].hard_blocked)
        self.assertFalse(states[1].is_wifi)

    def test_parse_link_state_prefers_administrative_flag(self):
        self.assertTrue(
            parse_link_is_up("4: wlan0: <BROADCAST,MULTICAST,UP> state DOWN")
        )
        self.assertFalse(parse_link_is_up("4: wlan0: <BROADCAST> state UP"))


class PlatformManagerTests(unittest.TestCase):
    def test_auto_selection_prefers_an_interface_already_up(self):
        responses = {
            ("iw", "dev"): result(("iw", "dev"), IW_OUTPUT),
            ("ip", "-o", "link", "show", "dev", "p2p0"): result(
                (), "5: p2p0: <BROADCAST> state DOWN"
            ),
            ("ip", "-o", "link", "show", "dev", "wlan0"): result(
                (), "4: wlan0: <BROADCAST> state DOWN"
            ),
            ("ip", "-o", "link", "show", "dev", "wlan1"): result(
                (), "7: wlan1: <BROADCAST,UP> state UP"
            ),
        }
        manager = PlatformManager(runner=FakeRunner(responses), is_android=False)

        self.assertEqual(manager.select_interface(), "wlan1")

    def test_prepare_and_restore_android_rfkill_and_link_state_once(self):
        rfkill_output = """0: phy0: Wireless LAN
  Soft blocked: yes
  Hard blocked: no
"""
        responses = {
            ("settings", "get", "global", "wifi_on"): result((), "0\n"),
            (
                "settings",
                "get",
                "global",
                "wifi_scan_always_enabled",
            ): result((), "1\n"),
            ("rfkill", "list"): result((), rfkill_output),
            ("iw", "dev"): result(
                (),
                "phy#0\n\tInterface wlan0\n\t\tifindex 4\n\t\ttype managed\n",
            ),
            ("ip", "-o", "link", "show", "dev", "wlan0"): result(
                (), "4: wlan0: <BROADCAST> state DOWN"
            ),
        }
        runner = FakeRunner(responses)
        manager = PlatformManager(
            "wlan0", runner=runner, is_android=True, poll_interval=0
        )

        self.assertEqual(manager.prepare(), "wlan0")
        self.assertEqual(manager.prepare(), "wlan0")
        self.assertEqual(manager.restore(), ())
        self.assertEqual(manager.restore(), ())

        commands = [call[0] for call in runner.calls]
        expected_once = [
            ("rfkill", "unblock", "0"),
            ("settings", "put", "global", "wifi_scan_always_enabled", "0"),
            ("svc", "wifi", "enable"),
            ("ip", "link", "set", "dev", "wlan0", "up"),
            ("ip", "link", "set", "dev", "wlan0", "down"),
            ("rfkill", "block", "0"),
            ("settings", "put", "global", "wifi_scan_always_enabled", "1"),
            ("svc", "wifi", "disable"),
        ]
        for command in expected_once:
            self.assertEqual(commands.count(command), 1, command)

    def test_requested_interface_must_exist(self):
        runner = FakeRunner({("iw", "dev"): result((), IW_OUTPUT)})
        manager = PlatformManager("wlan9", runner=runner, is_android=False)

        with self.assertRaises(PlatformError):
            manager.select_interface()


if __name__ == "__main__":
    unittest.main()
