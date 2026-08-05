import csv
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from wifit_core.models import (
    AccessPoint,
    AttackMethod,
    AttackOutcome,
    AttackResult,
    SecurityMode,
    WPSVersion,
    WPSVersionEvidence,
)
from wifit_core import reporter
from wifit_core.reporter import ReportFormat, ResultReporter


def sample_access_point(ssid="Café WiFi"):
    return AccessPoint(
        bssid="AA:BB:CC:DD:EE:FF",
        ssid=ssid,
        signal_dbm=-41.5,
        channel=6,
        frequency_mhz=2437,
        wps=True,
        wps_version=WPSVersion.VERSION_1,
        wps_version_evidence=WPSVersionEvidence.INFERRED,
        wps_locked=False,
        security=SecurityMode.WPA2,
        wsc_manufacturer="Acme",
        wsc_model_name="Gateway",
        vulnerability_reasons=["WPS 1.0 inferred (Version2 attribute absent)"],
    )


def sample_attack_results():
    started = datetime(2026, 8, 5, 4, 30, tzinfo=timezone.utc)
    return [
        AttackResult(
            method=AttackMethod.PIXIE_DUST,
            outcome=AttackOutcome.SUCCESS,
            bssid="AA:BB:CC:DD:EE:FF",
            ssid="Café WiFi",
            interface="wlan0",
            started_at=started,
            finished_at=started + timedelta(seconds=3.5),
            wps_pin="12345670",
            network_key="@secret-key",
            attempts=1,
            message="credentials recovered",
            metadata={"artifact": Path("capture.bin")},
        ),
        AttackResult(
            method=AttackMethod.PIN,
            outcome=AttackOutcome.FAILURE,
            bssid="00:11:22:33:44:55",
            ssid="Other AP",
            interface="wlan0",
            started_at=started,
            finished_at=started + timedelta(seconds=1),
            attempts=1,
            message="+registrar rejected PIN",
        ),
    ]


class ResultReporterTests(unittest.TestCase):
    def test_json_contains_scan_success_and_failure_and_uses_private_mode(self):
        with tempfile.TemporaryDirectory() as temporary_directory, mock.patch.object(
            reporter.os, "chmod", wraps=reporter.os.chmod
        ) as chmod:
            destination = ResultReporter().export(
                Path(temporary_directory) / "combined",
                access_points=[sample_access_point()],
                attack_results=sample_attack_results(),
                report_format=ReportFormat.JSON,
            )
            payload = json.loads(destination.read_text(encoding="utf-8"))

            self.assertEqual(destination.suffix, ".json")
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["scan_results"][0]["ssid"], "Café WiFi")
            self.assertEqual(
                [result["outcome"] for result in payload["attack_results"]],
                ["success", "failure"],
            )
            self.assertEqual(
                payload["attack_results"][0]["metadata"]["artifact"],
                "capture.bin",
            )
            self.assertTrue(
                any(
                    call.args[0] == destination and call.args[1] == 0o600
                    for call in chmod.call_args_list
                )
            )
            self.assertEqual(list(Path(temporary_directory).glob("*.tmp")), [])

    def test_csv_neutralizes_formula_cells_but_preserves_numeric_signal(self):
        access_point = sample_access_point("=HYPERLINK(\"https://invalid\")")
        attacks = sample_attack_results()

        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = ResultReporter().export(
                Path(temporary_directory) / "results.csv",
                access_points=[access_point],
                attack_results=attacks,
            )
            with destination.open("r", encoding="utf-8", newline="") as report_file:
                rows = list(csv.DictReader(report_file))

        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["ssid"], "'=HYPERLINK(\"https://invalid\")")
        self.assertEqual(rows[0]["signal_dbm"], "-41.5")
        self.assertEqual(rows[1]["network_key"], "'@secret-key")
        self.assertEqual(rows[2]["message"], "'+registrar rejected PIN")
        self.assertEqual(
            [row["record_type"] for row in rows], ["scan", "attack", "attack"]
        )

    def test_text_export_includes_wps_evidence_and_failed_attack(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = ResultReporter().export_scan(
                Path(temporary_directory) / "scan.txt", [sample_access_point()]
            )
            text = destination.read_text(encoding="utf-8")

            attacks_destination = ResultReporter().export_attacks(
                Path(temporary_directory) / "attacks.txt",
                sample_attack_results(),
            )
            attacks_text = attacks_destination.read_text(encoding="utf-8")

        self.assertIn("WPS: 1.0 (inferred); locked: no", text)
        self.assertIn("pixie-dust: success", attacks_text)
        self.assertIn("pin: failure", attacks_text)
        self.assertIn("Network key: @secret-key", attacks_text)

    def test_unknown_extension_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(ValueError, "Cannot infer report format"):
                ResultReporter().export(
                    Path(temporary_directory) / "report.xlsx",
                    access_points=[sample_access_point()],
                )


if __name__ == "__main__":
    unittest.main()
