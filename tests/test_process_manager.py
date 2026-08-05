import json
import os
from pathlib import Path
import signal
import stat
import tempfile
import unittest

from wifit_core.process_manager import ProcessManager, ProcessSnapshot


def make_executable(directory: Path, name: str = "wpa_supplicant") -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    executable = directory / f"{name}{suffix}"
    executable.write_bytes(b"placeholder")
    if os.name == "posix":
        executable.chmod(0o700)
    return executable.resolve()


class ProcessDiscoveryTests(unittest.TestCase):
    def test_procfs_discovery_preserves_nul_delimited_argv(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = make_executable(root)
            process_dir = root / "proc" / "222"
            process_dir.mkdir(parents=True)
            (process_dir / "cmdline").write_bytes(
                os.fsencode(executable)
                + b"\0-i\0wlan0\0--label\0Cafe WiFi\0"
            )
            (process_dir / "comm").write_text("wpa_supplicant\n", encoding="utf-8")
            stat_fields = ["S", *("0" for _ in range(18)), "98765"]
            (process_dir / "stat").write_text(
                f"222 (wpa_supplicant) {' '.join(stat_fields)}\n",
                encoding="ascii",
            )
            (process_dir / "status").write_text(
                f"Uid:\t{getattr(os, 'geteuid', lambda: 0)()}\t0\t0\t0\n",
                encoding="ascii",
            )
            manager = ProcessManager(
                proc_root=root / "proc",
                journal_path=root / "journal.json",
            )

            discovered = manager.discover()

            self.assertEqual(len(discovered), 1)
            self.assertEqual(
                discovered[0].argv,
                (str(executable), "-i", "wlan0", "--label", "Cafe WiFi"),
            )
            self.assertEqual(discovered[0].start_time_ticks, 98765)


class ProcessLifecycleTests(unittest.TestCase):
    def test_stop_escalates_journals_and_restore_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = make_executable(root)
            snapshot = ProcessSnapshot(
                pid=4242,
                name="wpa_supplicant",
                executable=str(executable),
                argv=(str(executable), "-i", "wlan0", "--label", "Cafe WiFi"),
                cwd=str(root),
                uid=getattr(os, "geteuid", lambda: 0)(),
                start_time_ticks=123,
            )
            alive = {snapshot.pid: True}
            signals = []
            spawns = []

            def send_signal(pid, sent_signal):
                signals.append((pid, sent_signal))
                # Some non-POSIX test hosts do not expose SIGKILL.  The second
                # delivery still proves that the bounded escalation path ran.
                if len(signals) == 2:
                    alive[pid] = False

            manager = ProcessManager(
                journal_path=root / "state" / "processes.json",
                terminate_timeout=0,
                kill_timeout=0,
                process_source=lambda: (snapshot,),
                process_alive=lambda item: alive.get(item.pid, False),
                signal_process=send_signal,
                spawn_process=lambda argv, cwd: spawns.append((tuple(argv), cwd)),
            )

            first_stop = manager.stop()
            second_stop = manager.stop()

            self.assertEqual(first_stop, second_stop)
            self.assertTrue(first_stop[0].terminated)
            self.assertEqual(signals[0], (4242, signal.SIGTERM))
            self.assertEqual(
                signals[1],
                (4242, getattr(signal, "SIGKILL", signal.SIGTERM)),
            )

            first_restore = manager.restore()
            second_restore = manager.restore()

            self.assertEqual(first_restore, (snapshot,))
            self.assertEqual(second_restore, ())
            self.assertEqual(
                spawns,
                [
                    (
                        (
                            str(executable),
                            "-i",
                            "wlan0",
                            "--label",
                            "Cafe WiFi",
                        ),
                        str(root),
                    )
                ],
            )

            journal_path = root / "state" / "processes.json"
            mode = stat.S_IMODE(journal_path.stat().st_mode)
            if os.name == "posix":
                self.assertEqual(mode & 0o077, 0)
            else:
                # Windows does not expose ACL restrictions through POSIX mode
                # bits; production Android/Termux does.
                self.assertTrue(journal_path.is_file())
            payload = json.loads(journal_path.read_text(encoding="utf-8"))
            self.assertFalse(payload["active"])
            self.assertEqual(
                payload["processes"][0]["snapshot"]["argv"][-1], "Cafe WiFi"
            )

    def test_context_restores_after_an_exception(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = make_executable(root)
            snapshot = ProcessSnapshot(
                pid=5252,
                name="wpa_supplicant",
                executable=str(executable),
                argv=(str(executable), "-i", "wlan0"),
            )
            alive = {snapshot.pid: True}
            spawns = []

            def send_signal(pid, sent_signal):
                alive[pid] = False

            manager = ProcessManager(
                journal_path=root / "journal.json",
                process_source=lambda: (snapshot,),
                process_alive=lambda item: alive.get(item.pid, False),
                signal_process=send_signal,
                spawn_process=lambda argv, cwd: spawns.append(tuple(argv)),
            )

            with self.assertRaisesRegex(RuntimeError, "attack failed"):
                with manager:
                    raise RuntimeError("attack failed")

            self.assertEqual(spawns, [snapshot.restore_argv])
            self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main()
