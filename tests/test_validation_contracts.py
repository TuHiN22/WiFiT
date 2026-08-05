"""Static release contracts for security and hardware-validation scripts.

These checks deliberately avoid invoking Bash, Android tooling, or privileged
commands so they run unchanged on Windows and POSIX test hosts.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_DIR = REPO_ROOT / "validation"

EXPECTED_V3_TEST_MODULES = (
    "tests/test_platform.py",
    "tests/test_process_manager.py",
    "tests/test_reporter.py",
    "tests/test_runner.py",
    "tests/test_scanner.py",
    "tests/test_vulnerability.py",
)


def _production_python_files() -> list[Path]:
    """Return every first-party Python source file, excluding tests."""

    return [REPO_ROOT / "wifit.py", *sorted((REPO_ROOT / "wifit_core").rglob("*.py"))]


def _os_import_aliases(tree: ast.AST) -> tuple[set[str], set[str]]:
    """Find names through which ``os.system`` could be called directly."""

    module_aliases: set[str] = set()
    system_aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for imported in node.names:
                if imported.name == "os":
                    module_aliases.add(imported.asname or "os")
        elif isinstance(node, ast.ImportFrom) and node.module == "os":
            for imported in node.names:
                if imported.name == "system":
                    system_aliases.add(imported.asname or "system")
    return module_aliases, system_aliases


def _is_os_system_call(
    node: ast.Call, module_aliases: set[str], system_aliases: set[str]
) -> bool:
    function = node.func
    if isinstance(function, ast.Name):
        return function.id in system_aliases
    return (
        isinstance(function, ast.Attribute)
        and function.attr == "system"
        and isinstance(function.value, ast.Name)
        and function.value.id in module_aliases
    )


def test_production_python_never_enables_a_command_shell() -> None:
    """Root-capable production code must not invoke an intermediary shell."""

    violations: list[str] = []
    for source_path in _production_python_files():
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        module_aliases, system_aliases = _os_import_aliases(tree)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            for keyword in node.keywords:
                if keyword.arg != "shell":
                    continue
                explicitly_false = (
                    isinstance(keyword.value, ast.Constant) and keyword.value.value is False
                )
                if not explicitly_false:
                    violations.append(
                        f"{source_path.relative_to(REPO_ROOT)}:{node.lineno}: "
                        "shell must never be true or dynamic"
                    )

            if _is_os_system_call(node, module_aliases, system_aliases):
                violations.append(
                    f"{source_path.relative_to(REPO_ROOT)}:{node.lineno}: os.system is forbidden"
                )

    assert not violations, "Unsafe shell execution found:\n" + "\n".join(violations)


def _logical_shell_source(source: str) -> str:
    """Join backslash-continuation lines for focused command inspection."""

    return re.sub(r"\\\r?\n[ \t]*", " ", source)


def _executes_mktemp_python_file(source: str) -> list[str]:
    """Return mktemp variables later passed to a Python interpreter."""

    logical_source = _logical_shell_source(source)
    temp_variables = re.findall(
        r"(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\$\(\s*mktemp\b",
        logical_source,
    )
    executed: list[str] = []
    for variable in temp_variables:
        variable_reference = rf"\$(?:{re.escape(variable)}|\{{{re.escape(variable)}\}})"
        python_invocation = rf"\bpython(?:3)?\b[^\n;]*{variable_reference}"
        if re.search(python_invocation, logical_source):
            executed.append(variable)
    return executed


def _exports_repo_pythonpath(source: str) -> bool:
    """Recognize an exported or command-scoped, preserving PYTHONPATH."""

    logical_source = _logical_shell_source(source)
    assignment_pattern = re.compile(
        r"(?m)(?P<prefix>^\s*(?:if\s+)?(?:export\s+|env\s+)?)"
        r"PYTHONPATH\s*=\s*(?P<rhs>[^\n;]+)"
    )
    existing_path = re.compile(r"\$(?:PYTHONPATH\b|\{PYTHONPATH(?=[:}]))")

    for assignment in assignment_pattern.finditer(logical_source):
        rhs = assignment.group("rhs")
        if "REPO_ROOT" not in rhs or existing_path.search(rhs) is None:
            continue

        prefix = assignment.group("prefix")
        if "export" in prefix or "env" in prefix:
            return True
        if re.search(r"\bpython(?:3)?\b", rhs):
            return True

        # Also accept a separate export after a preserving assignment.
        remainder = logical_source[assignment.end() :]
        if re.search(r"(?m)^\s*export\s+PYTHONPATH(?:\s|$)", remainder):
            return True
    return False


def _runs_python_stdin_from_repo(source: str) -> bool:
    """Recognize Python fed by a heredoc after changing to REPO_ROOT."""

    logical_source = _logical_shell_source(source)
    repo_cd = re.search(
        r"(?m)^\s*cd\s+(?:--\s+)?[\"']?\$(?:REPO_ROOT|\{REPO_ROOT\})[\"']?\s*$",
        logical_source,
    )
    stdin_python = re.search(
        r"(?m)^\s*(?:if\s+)?(?:[A-Za-z_][A-Za-z0-9_]*=[^\n ]+\s+)*"
        r"python(?:3)?\s+(?:-\s+[^<\n]*?)?<<-?\s*[\"']?[A-Za-z_][A-Za-z0-9_]*",
        logical_source,
    )
    return bool(repo_cd and stdin_python and repo_cd.start() < stdin_python.start())


def test_phase_python_helpers_have_a_repo_import_path() -> None:
    """Phase 2/3 helpers must import the checkout without relying on caller state."""

    failures: list[str] = []
    for script_name in ("02_test_scanner.sh", "03_test_pin_generation.sh"):
        script_path = VALIDATION_DIR / script_name
        source = script_path.read_text(encoding="utf-8")

        executed_temp_variables = _executes_mktemp_python_file(source)
        if executed_temp_variables:
            failures.append(
                f"{script_name} executes mktemp Python file(s): "
                f"{', '.join(executed_temp_variables)}"
            )

        if not (_exports_repo_pythonpath(source) or _runs_python_stdin_from_repo(source)):
            failures.append(
                f"{script_name} neither exports a preserving REPO_ROOT PYTHONPATH "
                "nor runs Python stdin after cd to REPO_ROOT"
            )

    assert not failures, "Invalid validation Python launch contract:\n" + "\n".join(failures)


def test_html_report_passes_summary_as_heredoc_python_argv() -> None:
    """The report generator must terminate its heredoc and pass JSON as argv[1]."""

    script_path = VALIDATION_DIR / "generate_html_report.sh"
    source = _logical_shell_source(script_path.read_text(encoding="utf-8"))
    python_command = r'(?:\bpython(?:3)?\b|["\']?\$PYTHON_BIN["\']?)'
    opener = re.search(
        rf"(?m)^(?P<command>[^\n]*{python_command}[^\n]*"
        r"<<-?\s*[\"']?(?P<delimiter>[A-Za-z_][A-Za-z0-9_]*)[\"']?[^\n]*)$",
        source,
    )
    assert opener is not None, "generate_html_report.sh has no Python heredoc invocation"

    command = opener.group("command")
    delimiter = opener.group("delimiter")
    assert re.search(rf"{python_command}\s+-\s+", command), (
        "heredoc Python must use '-' so following values are argv entries"
    )
    assert "$SUMMARY_JSON" in command, "SUMMARY_JSON must be passed to the Python command"
    assert command.index("$SUMMARY_JSON") < command.index("<<"), (
        "SUMMARY_JSON must be part of the Python argv before the heredoc redirection"
    )
    assert "sys.argv[1]" in source, "embedded Python must read SUMMARY_JSON from argv[1]"

    lines_after_opener = source[opener.end() :].splitlines()
    assert any(line.strip() == delimiter for line in lines_after_opener), (
        f"heredoc terminator {delimiter!r} must appear alone on its line"
    )
    malformed_terminators = [
        line.strip()
        for line in lines_after_opener
        if line.strip().startswith(delimiter) and line.strip() != delimiter
    ]
    assert not malformed_terminators, (
        "heredoc terminators cannot carry shell arguments: " + ", ".join(malformed_terminators)
    )


def test_clean_clone_contains_and_tracks_the_complete_v3_test_inventory() -> None:
    """Do not let locally present, untracked test coverage disappear from clones."""

    missing = [
        relative
        for relative in EXPECTED_V3_TEST_MODULES
        if not (REPO_ROOT / relative).is_file()
    ]
    assert not missing, "Expected test modules are missing: " + ", ".join(missing)

    git = shutil.which("git")
    if git is None or not (REPO_ROOT / ".git").exists():
        return

    completed = subprocess.run(
        [git, "-C", str(REPO_ROOT), "ls-files", "--", "tests"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.strip()
    tracked = {line.strip().replace("\\", "/") for line in completed.stdout.splitlines()}
    untracked = [relative for relative in EXPECTED_V3_TEST_MODULES if relative not in tracked]
    assert not untracked, "Test modules are present but untracked: " + ", ".join(untracked)
