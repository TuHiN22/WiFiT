import os
import sys
import time
import unittest

from wifit_core.runner import (
    CommandExecutionError,
    CommandRunner,
    CommandTimeoutError,
)


class CommandRunnerTests(unittest.TestCase):
    def test_preserves_argument_boundaries_and_captures_streams(self):
        runner = CommandRunner(default_timeout=3)
        result = runner.run(
            [
                sys.executable,
                "-c",
                ("import sys; print(sys.argv[1]); print(sys.argv[2], file=sys.stderr)"),
                "Cafe WiFi",
                "literal;$(not-a-shell)",
            ],
            check=True,
        )

        self.assertEqual(result.stdout.strip(), "Cafe WiFi")
        self.assertEqual(result.stderr.strip(), "literal;$(not-a-shell)")
        self.assertTrue(result.ok)
        self.assertIsInstance(result.argv, tuple)

    def test_rejects_command_strings(self):
        runner = CommandRunner()
        with self.assertRaises(TypeError):
            runner.run("python -V")  # type: ignore[arg-type]

    def test_check_raises_with_the_completed_result(self):
        runner = CommandRunner(default_timeout=3)
        with self.assertRaises(CommandExecutionError) as raised:
            runner.run(
                [sys.executable, "-c", "import sys; sys.exit(7)"],
                check=True,
            )

        self.assertEqual(raised.exception.result.returncode, 7)

    def test_timeout_is_finite_and_terminates_the_child(self):
        runner = CommandRunner(default_timeout=0.15, terminate_grace=0.1)
        started = time.monotonic()

        with self.assertRaises(CommandTimeoutError) as raised:
            runner.run(
                [sys.executable, "-c", "import time; time.sleep(10)"],
            )

        self.assertLess(time.monotonic() - started, 3)
        self.assertAlmostEqual(raised.exception.timeout, 0.15)

    def test_environment_is_merged_without_losing_the_parent_path(self):
        runner = CommandRunner(environment={"WIFIT_RUNNER_TEST": "base"})
        result = runner.run(
            [
                sys.executable,
                "-c",
                "import os; print(os.environ['WIFIT_RUNNER_TEST']); print(bool(os.environ.get('PATH')))",
            ],
            env={"WIFIT_RUNNER_TEST": "override"},
        )

        self.assertEqual(result.stdout.splitlines(), ["override", "True"])
        self.assertIn("PATH", os.environ)


if __name__ == "__main__":
    unittest.main()
