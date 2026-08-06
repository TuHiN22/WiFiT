"""Conservative discovery, suspension, and restoration of Wi-Fi processes."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_INTERFERERS = frozenset(
    {
        "connmand",
        "dhcpcd",
        "hostapd",
        "iwd",
        "networkmanager",
        "wicd",
        "wpa_supplicant",
    }
)


class ProcessManagerError(RuntimeError):
    """Base class for process lifecycle errors."""


class ProcessJournalError(ProcessManagerError):
    """The recovery journal could not be safely read or written."""


@dataclass(frozen=True, slots=True)
class ProcessSnapshot:
    """Enough immutable process metadata to avoid shell reconstruction."""

    pid: int
    name: str
    executable: str
    argv: tuple[str, ...]
    cwd: str | None = None
    uid: int | None = None
    start_time_ticks: int | None = None

    @property
    def restore_argv(self) -> tuple[str, ...]:
        # /proc/<pid>/cmdline preserves each original argument boundary.  Use
        # the trusted executable symlink for argv[0], which cannot be spoofed
        # through a process title.
        return (self.executable, *self.argv[1:])


@dataclass(slots=True)
class ManagedProcess:
    snapshot: ProcessSnapshot
    stop_requested: bool = False
    terminated: bool = False
    restored: bool = False
    error: str | None = None

    @property
    def pid(self) -> int:
        return self.snapshot.pid


ProcessSource = Callable[[], Iterable[ProcessSnapshot]]
ProcessAlive = Callable[[ProcessSnapshot], bool]
SignalProcess = Callable[[int, int], None]
SpawnProcess = Callable[[Sequence[str], str | None], object]


class ProcessManager:
    """Idempotent context manager for likely Wi-Fi interferers.

    Discovery requires an exact executable basename from a small allowlist,
    a recoverable absolute executable path, and NUL-delimited argv from procfs.
    PID start time is checked again before every signal to avoid PID-reuse
    races.  Only processes confirmed stopped by this instance are restored.
    """

    def __init__(
        self,
        *,
        interferers: Iterable[str] = DEFAULT_INTERFERERS,
        journal_path: str | os.PathLike[str] | None = None,
        proc_root: str | os.PathLike[str] = "/proc",
        terminate_timeout: float = 1.5,
        kill_timeout: float = 0.75,
        poll_interval: float = 0.05,
        process_source: ProcessSource | None = None,
        process_alive: ProcessAlive | None = None,
        signal_process: SignalProcess | None = None,
        spawn_process: SpawnProcess | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        for name, value in (
            ("terminate_timeout", terminate_timeout),
            ("kill_timeout", kill_timeout),
            ("poll_interval", poll_interval),
        ):
            if value < 0:
                raise ValueError(f"{name} may not be negative")

        self.interferers = frozenset(name.casefold() for name in interferers)
        if not self.interferers:
            raise ValueError("interferers may not be empty")
        self.proc_root = Path(proc_root)
        self.journal_path = (
            Path(journal_path) if journal_path is not None else self._default_journal()
        )
        self.terminate_timeout = terminate_timeout
        self.kill_timeout = kill_timeout
        self.poll_interval = poll_interval
        self._sleep = sleep
        self._monotonic = monotonic
        self._process_source = process_source or self._discover_procfs
        self._process_alive = process_alive or self._same_process
        self._signal_process = signal_process or os.kill
        self._spawn_process = spawn_process or self._spawn
        self._excluded_pids = {os.getpid(), os.getppid(), 0, 1}
        self._managed: list[ManagedProcess] = []
        self._active = False

    @staticmethod
    def _default_journal() -> Path:
        state_home = os.environ.get("XDG_STATE_HOME")
        base = Path(state_home) if state_home else Path.home() / ".local" / "state"
        return base / "wifit" / "process-journal.json"

    @property
    def managed(self) -> tuple[ManagedProcess, ...]:
        return tuple(self._managed)

    @property
    def active(self) -> bool:
        return self._active

    def discover(self) -> tuple[ProcessSnapshot, ...]:
        """Return only exact, restorable, permission-compatible matches."""

        unique: dict[int, ProcessSnapshot] = {}
        for snapshot in self._process_source():
            if self._eligible(snapshot):
                unique[snapshot.pid] = snapshot
        return tuple(unique[pid] for pid in sorted(unique))

    def stop(self) -> tuple[ManagedProcess, ...]:
        """Terminate discovered processes, escalating after a finite wait."""

        if self._active:
            return self.managed

        self._managed = [ManagedProcess(item) for item in self.discover()]
        self._active = True
        # Refuse to alter process state if a restrictive recovery journal
        # cannot first be established.
        self._write_journal()

        force_signal = getattr(signal, "SIGKILL", signal.SIGTERM)
        for managed in self._managed:
            snapshot = managed.snapshot
            if not self._process_alive(snapshot):
                continue
            managed.stop_requested = True
            self._write_journal()
            try:
                self._signal_process(snapshot.pid, signal.SIGTERM)
            except (OSError, PermissionError) as error:
                managed.error = f"SIGTERM failed: {error}"
                self._write_journal()
                continue

            exited = self._wait_for_exit(snapshot, self.terminate_timeout)
            if not exited:
                # Revalidate identity immediately before escalation.
                if not self._process_alive(snapshot):
                    exited = True
                else:
                    try:
                        self._signal_process(snapshot.pid, force_signal)
                    except (OSError, PermissionError) as error:
                        managed.error = f"forced termination failed: {error}"
                    else:
                        exited = self._wait_for_exit(snapshot, self.kill_timeout)

            if exited:
                managed.terminated = True
                managed.error = None
            elif managed.error is None:
                managed.error = "process remained alive after escalation"
            self._write_journal()
        return self.managed

    def restore(self) -> tuple[ProcessSnapshot, ...]:
        """Restore each process stopped by this manager at most once."""

        if not self._active:
            return ()
        restored: list[ProcessSnapshot] = []
        for managed in self._managed:
            if not managed.terminated or managed.restored:
                continue
            snapshot = managed.snapshot
            if self._equivalent_process_running(snapshot):
                managed.restored = True
                managed.error = None
                restored.append(snapshot)
                self._write_journal()
                continue
            try:
                self._spawn_process(snapshot.restore_argv, snapshot.cwd)
            except (OSError, ValueError) as error:
                managed.error = f"restore failed: {error}"
            else:
                managed.restored = True
                managed.error = None
                restored.append(snapshot)
            self._write_journal()

        self._active = any(item.terminated and not item.restored for item in self._managed)
        self._write_journal()
        return tuple(restored)

    def recover(self) -> tuple[ProcessSnapshot, ...]:
        """Restore processes left stopped by an interrupted prior run."""

        if self._active:
            return self.restore()
        payload = self._read_journal()
        if not payload or not payload.get("active"):
            return ()

        recovered: list[ManagedProcess] = []
        raw_processes = payload.get("processes")
        if not isinstance(raw_processes, list):
            raise ProcessJournalError("process journal has an invalid process list")
        for item in raw_processes:
            managed = self._managed_from_json(item)
            if managed is None or not self._eligible(managed.snapshot):
                continue
            # If the original identity is still alive, no restart is needed.
            if self._process_alive(managed.snapshot):
                managed.terminated = False
                managed.restored = True
            elif managed.stop_requested:
                managed.terminated = True
            recovered.append(managed)

        self._managed = recovered
        self._active = any(item.terminated and not item.restored for item in recovered)
        if not self._active:
            self._write_journal()
            return ()
        return self.restore()

    def _eligible(self, snapshot: ProcessSnapshot) -> bool:
        if snapshot.pid in self._excluded_pids or snapshot.pid < 2:
            return False
        if not snapshot.argv or not snapshot.executable:
            return False
        executable = Path(snapshot.executable)
        executable_name = executable.name.casefold()
        if executable_name.endswith(".exe"):
            executable_name = executable_name[:-4]
        if executable_name not in self.interferers:
            return False
        if not executable.is_absolute() or not executable.is_file():
            return False
        if os.name == "posix" and not os.access(executable, os.X_OK):
            return False
        get_euid = getattr(os, "geteuid", None)
        if get_euid is not None and snapshot.uid is not None:
            effective_uid = get_euid()
            if effective_uid != 0 and snapshot.uid != effective_uid:
                return False
        return True

    def _discover_procfs(self) -> Iterable[ProcessSnapshot]:
        try:
            entries = tuple(self.proc_root.iterdir())
        except OSError:
            return ()

        snapshots: list[ProcessSnapshot] = []
        for entry in entries:
            if not entry.name.isdigit():
                continue
            pid = int(entry.name)
            if pid in self._excluded_pids or pid < 2:
                continue
            try:
                raw_cmdline = (entry / "cmdline").read_bytes()
            except OSError:
                continue
            argv = tuple(
                chunk.decode("utf-8", errors="surrogateescape")
                for chunk in raw_cmdline.rstrip(b"\0").split(b"\0")
                if chunk
            )
            if not argv:
                continue
            try:
                name = (entry / "comm").read_text(encoding="utf-8", errors="replace").strip()
            except OSError:
                name = Path(argv[0]).name

            executable = self._read_link(entry / "exe")
            if executable is None and os.path.isabs(argv[0]):
                executable = argv[0]
            if executable is None:
                continue
            if executable.endswith(" (deleted)"):
                continue
            snapshots.append(
                ProcessSnapshot(
                    pid=pid,
                    name=name,
                    executable=executable,
                    argv=argv,
                    cwd=self._read_link(entry / "cwd"),
                    uid=self._read_uid(entry / "status"),
                    start_time_ticks=self._read_start_time(entry / "stat"),
                )
            )
        return snapshots

    def _same_process(self, snapshot: ProcessSnapshot) -> bool:
        process_dir = self.proc_root / str(snapshot.pid)
        if not process_dir.exists():
            return False
        if snapshot.start_time_ticks is not None:
            current = self._read_start_time(process_dir / "stat")
            return current == snapshot.start_time_ticks
        try:
            os.kill(snapshot.pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    def _wait_for_exit(self, snapshot: ProcessSnapshot, timeout: float) -> bool:
        deadline = self._monotonic() + timeout
        while self._process_alive(snapshot):
            remaining = deadline - self._monotonic()
            if remaining <= 0:
                return False
            self._sleep(min(self.poll_interval, remaining))
        return True

    def _equivalent_process_running(self, original: ProcessSnapshot) -> bool:
        for candidate in self.discover():
            if candidate.restore_argv == original.restore_argv and self._process_alive(candidate):
                return True
        return False

    @staticmethod
    def _spawn(argv: Sequence[str], cwd: str | None) -> subprocess.Popen[bytes]:
        usable_cwd = cwd if cwd and Path(cwd).is_dir() else None
        popen_kwargs: dict[str, object] = {
            "cwd": usable_cwd,
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "close_fds": True,
        }
        if os.name == "posix":
            popen_kwargs["start_new_session"] = True
        elif os.name == "nt":  # pragma: no cover - Android is POSIX
            # Type ignore: CREATE_NEW_PROCESS_GROUP is Windows-only
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined,unused-ignore]
        # Type ignore: popen_kwargs dict is dynamically constructed
        return subprocess.Popen(list(argv), **popen_kwargs)  # type: ignore[call-overload,no-any-return,unused-ignore]

    @staticmethod
    def _read_link(path: Path) -> str | None:
        try:
            return os.readlink(path)
        except OSError:
            return None

    @staticmethod
    def _read_uid(path: Path) -> int | None:
        try:
            lines = path.read_text(encoding="ascii", errors="replace").splitlines()
        except OSError:
            return None
        for line in lines:
            if line.startswith("Uid:"):
                fields = line.split()
                if len(fields) > 1 and fields[1].isdigit():
                    return int(fields[1])
        return None

    @staticmethod
    def _read_start_time(path: Path) -> int | None:
        try:
            stat_line = path.read_text(encoding="ascii", errors="replace").strip()
        except OSError:
            return None
        closing_parenthesis = stat_line.rfind(")")
        if closing_parenthesis < 0:
            return None
        # Fields after the command name begin at proc field 3.  Start time is
        # field 22, therefore index 19 in this suffix.
        fields = stat_line[closing_parenthesis + 1 :].split()
        if len(fields) <= 19:
            return None
        try:
            return int(fields[19])
        except ValueError:
            return None

    def _journal_payload(self) -> dict[str, object]:
        processes: list[dict[str, object]] = []
        for managed in self._managed:
            snapshot = asdict(managed.snapshot)
            snapshot["argv"] = list(managed.snapshot.argv)
            processes.append(
                {
                    "snapshot": snapshot,
                    "stop_requested": managed.stop_requested,
                    "terminated": managed.terminated,
                    "restored": managed.restored,
                    "error": managed.error,
                }
            )
        return {
            "version": 1,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "active": self._active,
            "processes": processes,
        }

    def _write_journal(self) -> None:
        parent = self.journal_path.parent
        try:
            parent_existed = parent.exists()
            parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            if not parent_existed:
                os.chmod(parent, 0o700)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{self.journal_path.name}.", dir=parent, text=True
            )
            try:
                os.fchmod(descriptor, 0o600)  # type: ignore[attr-defined]
                with os.fdopen(descriptor, "w", encoding="utf-8") as journal:
                    json.dump(
                        self._journal_payload(),
                        journal,
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    )
                    journal.write("\n")
                    journal.flush()
                    os.fsync(journal.fileno())
                os.replace(temporary_name, self.journal_path)
                os.chmod(self.journal_path, 0o600)
            except Exception:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                try:
                    os.unlink(temporary_name)
                except OSError:
                    pass
                raise
        except OSError as error:
            raise ProcessJournalError(
                f"could not write process journal {self.journal_path}: {error}"
            ) from error

    def _read_journal(self) -> dict[str, object] | None:
        try:
            raw = self.journal_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError as error:
            raise ProcessJournalError(
                f"could not read process journal {self.journal_path}: {error}"
            ) from error
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ProcessJournalError("process journal is not valid JSON") from error
        if not isinstance(payload, dict) or payload.get("version") != 1:
            raise ProcessJournalError("unsupported process journal format")
        return payload

    @staticmethod
    def _managed_from_json(item: object) -> ManagedProcess | None:
        if not isinstance(item, dict):
            return None
        snapshot_data = item.get("snapshot")
        if not isinstance(snapshot_data, dict):
            return None
        argv = snapshot_data.get("argv")
        if not isinstance(argv, list) or not all(isinstance(arg, str) for arg in argv):
            return None
        try:
            snapshot = ProcessSnapshot(
                pid=int(snapshot_data["pid"]),
                name=str(snapshot_data["name"]),
                executable=str(snapshot_data["executable"]),
                argv=tuple(argv),
                cwd=(str(snapshot_data["cwd"]) if snapshot_data.get("cwd") is not None else None),
                uid=(int(snapshot_data["uid"]) if snapshot_data.get("uid") is not None else None),
                start_time_ticks=(
                    int(snapshot_data["start_time_ticks"])
                    if snapshot_data.get("start_time_ticks") is not None
                    else None
                ),
            )
        except (KeyError, TypeError, ValueError):
            return None
        return ManagedProcess(
            snapshot=snapshot,
            stop_requested=bool(item.get("stop_requested", False)),
            terminated=bool(item.get("terminated", False)),
            restored=bool(item.get("restored", False)),
            error=str(item["error"]) if item.get("error") is not None else None,
        )

    def __enter__(self) -> ProcessManager:
        self.stop()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.restore()


InterferingProcessManager = ProcessManager


__all__ = [
    "DEFAULT_INTERFERERS",
    "InterferingProcessManager",
    "ManagedProcess",
    "ProcessJournalError",
    "ProcessManager",
    "ProcessManagerError",
    "ProcessSnapshot",
]
