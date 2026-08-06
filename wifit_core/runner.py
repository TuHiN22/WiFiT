"""Small, bounded subprocess execution primitives.

The rest of WiFiT uses this module instead of constructing shell command
strings.  Every command has a finite deadline and receives an explicit argv
sequence, which keeps quoting decisions at the operating-system boundary.
"""

from __future__ import annotations

import math
import os
import signal
import subprocess
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

Arg = str | os.PathLike[str]


@dataclass(frozen=True, slots=True)
class CommandResult:
    """The stable subset of ``CompletedProcess`` used by WiFiT."""

    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def args(self) -> tuple[str, ...]:
        """Compatibility spelling used by :mod:`subprocess`."""

        return self.argv

    def check_returncode(self) -> None:
        if not self.ok:
            raise CommandExecutionError(self)


class CommandError(RuntimeError):
    """Base class for failures at the process boundary."""

    def __init__(self, message: str, argv: Sequence[str]) -> None:
        super().__init__(message)
        self.argv = tuple(argv)


class CommandLaunchError(CommandError):
    """A command could not be started."""

    def __init__(self, argv: Sequence[str], error: OSError) -> None:
        super().__init__(f"failed to start {argv[0]!r}: {error}", argv)
        self.error = error


class CommandNotFoundError(CommandLaunchError):
    """The requested executable does not exist."""


class CommandTimeoutError(CommandError):
    """A command exceeded its deadline and was terminated."""

    def __init__(
        self,
        argv: Sequence[str],
        timeout: float,
        stdout: str,
        stderr: str,
    ) -> None:
        super().__init__(f"command {argv[0]!r} exceeded its {timeout:g}s timeout", argv)
        self.timeout = timeout
        self.stdout = stdout
        self.stderr = stderr


class CommandExecutionError(CommandError):
    """A command completed with a non-zero status."""

    def __init__(self, result: CommandResult) -> None:
        super().__init__(
            f"command {result.argv[0]!r} exited with status {result.returncode}",
            result.argv,
        )
        self.result = result


# Short aliases make the exceptions pleasant to use without sacrificing the
# descriptive public names above.
CommandTimedOut = CommandTimeoutError
CommandFailed = CommandExecutionError


class CommandRunner:
    """Execute argv lists with captured output and a mandatory deadline."""

    def __init__(
        self,
        *,
        default_timeout: float = 15.0,
        terminate_grace: float = 0.5,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        self.default_timeout = self._validate_timeout(default_timeout, name="default_timeout")
        self.terminate_grace = self._validate_timeout(
            terminate_grace, name="terminate_grace", allow_zero=True
        )
        self.environment = dict(environment or {})

    def run(
        self,
        argv: Sequence[Arg],
        *,
        timeout: float | None = None,
        check: bool = False,
        input_text: str | None = None,
        cwd: Arg | None = None,
        env: Mapping[str, str] | None = None,
    ) -> CommandResult:
        """Run ``argv`` without a shell.

        ``argv`` must be a non-empty sequence; passing a command string is an
        error.  ``None`` selects the runner's finite default timeout and never
        disables deadline enforcement.
        """

        normalised = self.normalise_argv(argv)
        deadline = (
            self.default_timeout
            if timeout is None
            else self._validate_timeout(timeout, name="timeout")
        )
        child_env = os.environ.copy()
        child_env.update(self.environment)
        if env:
            child_env.update({str(key): str(value) for key, value in env.items()})

        popen_kwargs: dict[str, object] = {
            "stdin": subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "cwd": os.fspath(cwd) if cwd is not None else None,
            "env": child_env,
            "close_fds": True,
        }
        if os.name == "posix":
            # A private session lets timeout cleanup include descendants that
            # inherited our output pipes.
            popen_kwargs["start_new_session"] = True
        elif os.name == "nt":  # pragma: no cover - platform-specific flag
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        started = time.monotonic()
        try:
            process = subprocess.Popen(list(normalised), **popen_kwargs)
        except FileNotFoundError as error:
            raise CommandNotFoundError(normalised, error) from error
        except OSError as error:
            raise CommandLaunchError(normalised, error) from error

        try:
            stdout, stderr = process.communicate(input=input_text, timeout=deadline)
        except subprocess.TimeoutExpired:
            stdout, stderr = self._stop_timed_out_process(process)
            raise CommandTimeoutError(normalised, deadline, stdout or "", stderr or "") from None

        result = CommandResult(
            argv=normalised,
            returncode=process.returncode,
            stdout=stdout or "",
            stderr=stderr or "",
            duration_seconds=time.monotonic() - started,
        )
        if check:
            result.check_returncode()
        return result

    @staticmethod
    def normalise_argv(argv: Sequence[Arg]) -> tuple[str, ...]:
        """Validate and freeze an argv sequence."""

        if isinstance(argv, (str, bytes, os.PathLike)):
            raise TypeError("argv must be a sequence of arguments, not a command string")

        values: list[str] = []
        for argument in argv:
            value = os.fspath(argument)
            if isinstance(value, bytes):
                raise TypeError("argv entries must be text, not bytes")
            if "\x00" in value:
                raise ValueError("argv entries may not contain NUL bytes")
            values.append(value)
        if not values or not values[0]:
            raise ValueError("argv must contain a non-empty executable")
        return tuple(values)

    @staticmethod
    def _validate_timeout(value: float, *, name: str, allow_zero: bool = False) -> float:
        if isinstance(value, bool):
            raise TypeError(f"{name} must be a finite number")
        timeout = float(value)
        minimum_ok = timeout >= 0 if allow_zero else timeout > 0
        if not minimum_ok or not math.isfinite(timeout):
            qualifier = "non-negative" if allow_zero else "positive"
            raise ValueError(f"{name} must be a finite {qualifier} number")
        return timeout

    def _stop_timed_out_process(self, process: subprocess.Popen[str]) -> tuple[str, str]:
        self._signal_process_group(process, force=False)
        try:
            return process.communicate(timeout=self.terminate_grace)
        except subprocess.TimeoutExpired:
            self._signal_process_group(process, force=True)
            # A force-killed private process group should promptly close its
            # inherited pipes.  The direct kill is a final race-safe fallback.
            try:
                return process.communicate(timeout=max(self.terminate_grace, 0.1))
            except subprocess.TimeoutExpired:  # pragma: no cover - rare OS race
                process.kill()
                return process.communicate()

    @staticmethod
    def _signal_process_group(process: subprocess.Popen[str], *, force: bool) -> None:
        if process.poll() is not None:
            return
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL if force else signal.SIGTERM)
            elif force:
                process.kill()
            else:
                process.terminate()
        except ProcessLookupError:
            return
        except OSError:
            # The child may have exited between poll() and signal delivery, or
            # the platform may not expose process groups as expected.
            if process.poll() is None:
                if force:
                    process.kill()
                else:
                    process.terminate()


Runner = CommandRunner


__all__ = [
    "CommandError",
    "CommandExecutionError",
    "CommandFailed",
    "CommandLaunchError",
    "CommandNotFoundError",
    "CommandResult",
    "CommandRunner",
    "CommandTimedOut",
    "CommandTimeoutError",
    "Runner",
]
