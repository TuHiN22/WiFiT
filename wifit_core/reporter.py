"""Atomic UTF-8 reporting for scan and attack results."""

from __future__ import annotations

from collections.abc import Iterable
import csv
from datetime import datetime, timezone
from enum import Enum
import io
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .models import AccessPoint, AttackResult


class ReportFormat(str, Enum):
    TXT = "txt"
    CSV = "csv"
    JSON = "json"


_CSV_FIELDS = (
    "record_type",
    "bssid",
    "ssid",
    "signal_dbm",
    "channel",
    "frequency_mhz",
    "wps",
    "wps_version",
    "wps_version_evidence",
    "wps_locked",
    "security",
    "wpa3",
    "wpa3_transition",
    "wsc_manufacturer",
    "wsc_model_name",
    "wsc_model_number",
    "wsc_device_name",
    "vulnerability_reasons",
    "attack_method",
    "attack_outcome",
    "interface",
    "started_at",
    "finished_at",
    "duration_seconds",
    "wps_pin",
    "network_key",
    "attempts",
    "message",
    "metadata",
)
_DANGEROUS_CSV_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
_SENSITIVE_METADATA_TOKENS = ("password", "psk", "pin", "key", "credential", "secret")


def _resolve_format(path: Path, report_format: ReportFormat | str | None) -> ReportFormat:
    if report_format is not None:
        if isinstance(report_format, ReportFormat):
            return report_format
        try:
            return ReportFormat(str(report_format).casefold().lstrip("."))
        except ValueError as error:
            raise ValueError(f"Unsupported report format: {report_format!r}") from error

    suffix = path.suffix.casefold().lstrip(".")
    if not suffix:
        return ReportFormat.JSON
    try:
        return ReportFormat(suffix)
    except ValueError as error:
        raise ValueError(f"Cannot infer report format from {path.name!r}") from error


def _json_default(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, set):
        return sorted(value, key=str)
    return str(value)


def _csv_safe(value: Any) -> str:
    """Serialize one cell and neutralize spreadsheet formula prefixes."""

    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, tuple, set)):
        text = " | ".join(str(item) for item in value)
    elif isinstance(value, dict):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=_json_default)
    else:
        text = str(value)

    formula_probe = text.lstrip().lstrip("\ufeff").lstrip()
    if formula_probe.startswith(_DANGEROUS_CSV_PREFIXES):
        return "'" + text
    return text


def _text_safe(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\r", "\\r").replace("\n", "\\n")


def _metadata_looks_sensitive(value: Any, key: str = "") -> bool:
    normalized_key = key.casefold()
    if any(token in normalized_key for token in _SENSITIVE_METADATA_TOKENS):
        return value not in (None, "", [], {}, ())
    if isinstance(value, dict):
        return any(
            _metadata_looks_sensitive(child, str(child_key))
            for child_key, child in value.items()
        )
    if isinstance(value, (list, tuple, set)):
        return any(_metadata_looks_sensitive(child, key) for child in value)
    return False


def _atomic_write(path: Path, content: str, mode: int) -> None:
    """Replace ``path`` atomically using a same-directory private temp file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        try:
            os.chmod(temporary_name, mode)
        except OSError:
            # Some Android/virtual filesystems do not expose POSIX permissions.
            pass
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as report_file:
            descriptor = -1
            report_file.write(content)
            report_file.flush()
            os.fsync(report_file.fileno())
        os.replace(temporary_name, path)
        try:
            os.chmod(path, mode)
        except OSError:
            pass
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


class ResultReporter:
    """Export complete scan and success/failure attack records."""

    def export(
        self,
        path: str | Path,
        *,
        access_points: Iterable[AccessPoint] = (),
        attack_results: Iterable[AttackResult] = (),
        report_format: ReportFormat | str | None = None,
    ) -> Path:
        destination = Path(path)
        scans = list(access_points)
        attacks = list(attack_results)
        resolved_format = _resolve_format(destination, report_format)

        if not destination.suffix:
            destination = destination.with_suffix(f".{resolved_format.value}")

        generated_at = datetime.now(timezone.utc)
        if resolved_format is ReportFormat.JSON:
            content = self._render_json(scans, attacks, generated_at)
        elif resolved_format is ReportFormat.CSV:
            content = self._render_csv(scans, attacks)
        else:
            content = self._render_text(scans, attacks, generated_at)

        contains_credentials = any(result.contains_credentials for result in attacks)
        contains_sensitive_metadata = any(
            _metadata_looks_sensitive(result.metadata) for result in attacks
        )
        mode = 0o600 if contains_credentials or contains_sensitive_metadata else 0o644
        _atomic_write(destination, content, mode)
        return destination

    def export_scan(
        self,
        path: str | Path,
        access_points: Iterable[AccessPoint],
        *,
        report_format: ReportFormat | str | None = None,
    ) -> Path:
        return self.export(
            path, access_points=access_points, report_format=report_format
        )

    def export_attacks(
        self,
        path: str | Path,
        attack_results: Iterable[AttackResult],
        *,
        report_format: ReportFormat | str | None = None,
    ) -> Path:
        return self.export(
            path, attack_results=attack_results, report_format=report_format
        )

    @staticmethod
    def _render_json(
        scans: list[AccessPoint],
        attacks: list[AttackResult],
        generated_at: datetime,
    ) -> str:
        payload = {
            "schema_version": 1,
            "generated_at": generated_at.isoformat(),
            "scan_results": [access_point.to_record() for access_point in scans],
            "attack_results": [result.to_record() for result in attacks],
        }
        return json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
            default=_json_default,
        ) + "\n"

    @staticmethod
    def _render_csv(
        scans: list[AccessPoint], attacks: list[AttackResult]
    ) -> str:
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()

        for access_point in scans:
            record = access_point.to_record()
            record["record_type"] = "scan"
            writer.writerow({key: _csv_safe(record.get(key)) for key in _CSV_FIELDS})

        for result in attacks:
            attack_record = result.to_record()
            record = {
                "record_type": "attack",
                "bssid": attack_record["bssid"],
                "ssid": attack_record["ssid"],
                "attack_method": attack_record["method"],
                "attack_outcome": attack_record["outcome"],
                "interface": attack_record["interface"],
                "started_at": attack_record["started_at"],
                "finished_at": attack_record["finished_at"],
                "duration_seconds": attack_record["duration_seconds"],
                "wps_pin": attack_record["wps_pin"],
                "network_key": attack_record["network_key"],
                "attempts": attack_record["attempts"],
                "message": attack_record["message"],
                "metadata": attack_record["metadata"],
            }
            writer.writerow({key: _csv_safe(record.get(key)) for key in _CSV_FIELDS})
        return stream.getvalue()

    @staticmethod
    def _render_text(
        scans: list[AccessPoint],
        attacks: list[AttackResult],
        generated_at: datetime,
    ) -> str:
        lines = [
            "WiFiT scan and attack report",
            f"Generated (UTC): {generated_at.isoformat()}",
            "",
            f"Scan results ({len(scans)})",
        ]
        for index, access_point in enumerate(scans, start=1):
            version = (
                f"{access_point.wps_version.value} "
                f"({access_point.wps_version_evidence.value})"
                if access_point.wps_version
                else "n/a"
            )
            lock_state = (
                "unknown"
                if access_point.wps_locked is None
                else "yes" if access_point.wps_locked else "no"
            )
            lines.extend(
                (
                    f"[{index}] {_text_safe(access_point.ssid)} ({access_point.bssid})",
                    f"  Signal/channel: {access_point.signal_dbm} dBm / {access_point.channel}",
                    f"  Security: {access_point.security.value}",
                    f"  WPS: {version}; locked: {lock_state}",
                    "  WSC: "
                    + _text_safe(
                        " ".join(
                            value
                            for value in (
                                access_point.wsc_manufacturer,
                                access_point.wsc_model_name,
                                access_point.wsc_model_number,
                                access_point.wsc_device_name,
                            )
                            if value
                        )
                    ),
                    "  Vulnerability reasons: "
                    + (_text_safe("; ".join(access_point.vulnerability_reasons)) or "none"),
                )
            )

        lines.extend(("", f"Attack results ({len(attacks)})"))
        for index, result in enumerate(attacks, start=1):
            lines.extend(
                (
                    f"[{index}] {result.method.value}: {result.outcome.value}",
                    f"  Target: {_text_safe(result.ssid)} ({_text_safe(result.bssid)})",
                    "  Interface/attempts: "
                    f"{_text_safe(result.interface)} / {_text_safe(result.attempts)}",
                    f"  WPS PIN: {_text_safe(result.wps_pin)}",
                    f"  Network key: {_text_safe(result.network_key)}",
                    f"  Message: {_text_safe(result.message)}",
                )
            )
        return "\n".join(lines) + "\n"


# Short compatibility name for callers that already use ``Reporter``.
Reporter = ResultReporter


def export_report(
    path: str | Path,
    *,
    access_points: Iterable[AccessPoint] = (),
    attack_results: Iterable[AttackResult] = (),
    report_format: ReportFormat | str | None = None,
) -> Path:
    """Convenience wrapper around ``ResultReporter.export``."""

    return ResultReporter().export(
        path,
        access_points=access_points,
        attack_results=attack_results,
        report_format=report_format,
    )
