from contextlib import ExitStack, contextmanager
import io
import posixpath
import unittest
from unittest import mock

import wifit


class ExecReplaced(BaseException):
    """Stop a mocked successful exec without being caught as an OSError."""


class RootElevationTests(unittest.TestCase):
    @contextmanager
    def _patched_environment(self, argv=None, which_paths=None, executable=None):
        prefix = "/data/data/com.termux/files/usr"
        paths = {
            "sudo": prefix + "/bin/sudo",
            "python3": prefix + "/bin/python3",
        }
        if which_paths:
            paths.update(which_paths)

        def realpath(path):
            # Model the actual sudo -> tsu symlink.  Production must never ask
            # realpath() to resolve the sudo alias itself.
            if path == prefix + "/bin/sudo":
                return prefix + "/bin/tsu"
            return path

        # The production platform is POSIX/Termux.  Force POSIX path joining
        # so these tests exercise the same candidate de-duplication on Windows.
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(wifit, "check_root", return_value=False))
            stack.enter_context(mock.patch.dict(wifit.os.environ, {"PREFIX": prefix}))
            stack.enter_context(
                mock.patch.object(
                    wifit.sys,
                    "executable",
                    prefix + "/bin/python3" if executable is None else executable,
                )
            )
            stack.enter_context(mock.patch.object(wifit.sys, "argv", argv or ["wifit.py"]))
            stack.enter_context(mock.patch.object(wifit, "__file__", prefix + "/bin/wifit.py"))
            stack.enter_context(mock.patch.object(wifit.shutil, "which", side_effect=paths.get))
            stack.enter_context(
                mock.patch.object(wifit.os.path, "join", side_effect=posixpath.join)
            )
            stack.enter_context(
                mock.patch.object(wifit.os.path, "isabs", side_effect=posixpath.isabs)
            )
            stack.enter_context(mock.patch.object(wifit.os.path, "isfile", return_value=True))
            stack.enter_context(mock.patch.object(wifit.os, "access", return_value=True))
            stack.enter_context(mock.patch.object(wifit.os.path, "realpath", side_effect=realpath))
            stack.enter_context(mock.patch("sys.stdout", new_callable=io.StringIO))
            stack.enter_context(mock.patch("sys.stderr", new_callable=io.StringIO))
            yield

    def test_uses_tsu_sudo_alias_for_one_shot_elevation(self):
        prefix = "/data/data/com.termux/files/usr"
        execv = mock.Mock(side_effect=ExecReplaced)

        with (
            self._patched_environment(["wifit.py", "--target", "Cafe WiFi"]),
            mock.patch.object(wifit.os, "execv", execv),
        ):
            with self.assertRaises(ExecReplaced):
                wifit.get_root_access()

        execv.assert_called_once_with(
            prefix + "/bin/sudo",
            [
                prefix + "/bin/sudo",
                prefix + "/bin/python3",
                prefix + "/bin/wifit.py",
                "--target",
                "Cafe WiFi",
            ],
        )

    def test_falls_back_to_sudo_found_on_path_after_launch_error(self):
        prefix = "/data/data/com.termux/files/usr"
        fallback_sudo = "/alternate/termux/bin/sudo"
        execv = mock.Mock(side_effect=[FileNotFoundError("sudo missing"), ExecReplaced])

        with (
            self._patched_environment(
                ["wifit.py", "--target", "Cafe WiFi"], which_paths={"sudo": fallback_sudo}
            ),
            mock.patch.object(wifit.os, "execv", execv),
        ):
            with self.assertRaises(ExecReplaced):
                wifit.get_root_access()

        self.assertEqual(execv.call_count, 2)
        fallback_args = execv.call_args_list[1][0]
        self.assertEqual(
            fallback_args,
            (
                fallback_sudo,
                [
                    fallback_sudo,
                    prefix + "/bin/python3",
                    prefix + "/bin/wifit.py",
                    "--target",
                    "Cafe WiFi",
                ],
            ),
        )

    def test_resolves_relative_python_before_elevation(self):
        prefix = "/data/data/com.termux/files/usr"
        execv = mock.Mock(side_effect=ExecReplaced)

        with (
            self._patched_environment(executable="python3"),
            mock.patch.object(wifit.os, "execv", execv),
        ):
            with self.assertRaises(ExecReplaced):
                wifit.get_root_access()

        command = execv.call_args[0][1]
        self.assertEqual(command[1], prefix + "/bin/python3")

    def test_does_nothing_when_already_root(self):
        with (
            mock.patch.object(wifit, "check_root", return_value=True),
            mock.patch.object(wifit.os, "execv") as execv,
        ):
            self.assertTrue(wifit.get_root_access())
            execv.assert_not_called()


if __name__ == "__main__":
    unittest.main()
