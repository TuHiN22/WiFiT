"""Validated pixiewps execution for WPS Pixie Dust attacks.

Provides parameter validation, command construction, and output parsing for
pixiewps invocations. All subprocess calls use bounded timeouts.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Sequence

from .runner import CommandRunner, CommandTimeoutError, CommandExecutionError


_PIN_RE = re.compile(r"WPS\s+pin:\s*([0-9]{8})", re.IGNORECASE)
_PIXIEWPS_MIN_TIMEOUT = 10.0
_PIXIEWPS_DEFAULT_TIMEOUT = 120.0


@dataclass(frozen=True, slots=True)
class PixiewpsParameters:
    """Complete Pixie Dust parameters for pixiewps."""
    
    pke: str
    pkr: str
    e_hash1: str
    e_hash2: str
    authkey: str
    e_nonce: str
    
    def validate(self) -> list[str]:
        """Return list of validation errors (empty if valid)."""
        errors = []
        
        # All parameters must be non-empty hex strings
        for name, value in [
            ("PKE", self.pke),
            ("PKR", self.pkr),
            ("E-Hash1", self.e_hash1),
            ("E-Hash2", self.e_hash2),
            ("AuthKey", self.authkey),
            ("E-Nonce", self.e_nonce),
        ]:
            if not value:
                errors.append(f"{name} is empty")
            elif not all(c in "0123456789ABCDEFabcdef" for c in value):
                errors.append(f"{name} contains non-hex characters")
        
        # Length validation (typical lengths from WPS spec)
        if self.pke and len(self.pke) != 192:
            errors.append(f"PKE should be 192 hex chars, got {len(self.pke)}")
        
        if self.pkr and len(self.pkr) != 192:
            errors.append(f"PKR should be 192 hex chars, got {len(self.pkr)}")
        
        if self.e_hash1 and len(self.e_hash1) != 64:
            errors.append(f"E-Hash1 should be 64 hex chars, got {len(self.e_hash1)}")
        
        if self.e_hash2 and len(self.e_hash2) != 64:
            errors.append(f"E-Hash2 should be 64 hex chars, got {len(self.e_hash2)}")
        
        if self.authkey and len(self.authkey) != 64:
            errors.append(f"AuthKey should be 64 hex chars, got {len(self.authkey)}")
        
        if self.e_nonce and len(self.e_nonce) != 32:
            errors.append(f"E-Nonce should be 32 hex chars, got {len(self.e_nonce)}")
        
        return errors


@dataclass(frozen=True, slots=True)
class PixiewpsResult:
    """Result of pixiewps execution."""
    
    success: bool
    pin: str | None
    duration_seconds: float
    stdout: str
    stderr: str
    error_message: str | None = None
    
    @property
    def failed(self) -> bool:
        return not self.success


def run_pixiewps(
    params: PixiewpsParameters,
    *,
    runner: CommandRunner | None = None,
    timeout: float = _PIXIEWPS_DEFAULT_TIMEOUT,
    force: bool = False,
    small_dh_keys: bool = False,
) -> PixiewpsResult:
    """Execute pixiewps with validated parameters.
    
    Args:
        params: Complete Pixie Dust parameters
        runner: CommandRunner instance (creates default if None)
        timeout: Execution timeout in seconds (min 10s)
        force: Enable --force flag for full keyspace search
        small_dh_keys: Enable -S flag for small DH keys
    
    Returns:
        PixiewpsResult with PIN if successful
    
    Raises:
        ValueError: If parameters fail validation
    """
    # Validate parameters
    validation_errors = params.validate()
    if validation_errors:
        raise ValueError(f"Invalid pixiewps parameters: {'; '.join(validation_errors)}")
    
    # Enforce minimum timeout
    timeout = max(timeout, _PIXIEWPS_MIN_TIMEOUT)
    
    if runner is None:
        runner = CommandRunner()
    
    # Build command
    cmd = [
        "pixiewps",
        "--pke", params.pke,
        "--pkr", params.pkr,
        "--e-hash1", params.e_hash1,
        "--e-hash2", params.e_hash2,
        "--authkey", params.authkey,
        "--e-nonce", params.e_nonce,
    ]
    
    if force:
        cmd.append("--force")
    
    if small_dh_keys:
        cmd.append("-S")
    
    # Execute
    try:
        result = runner.run(cmd, timeout=timeout)
    except CommandTimeoutError as e:
        return PixiewpsResult(
            success=False,
            pin=None,
            duration_seconds=timeout,
            stdout=e.stdout if hasattr(e, 'stdout') else "",
            stderr=e.stderr if hasattr(e, 'stderr') else "",
            error_message=f"pixiewps exceeded {timeout}s timeout",
        )
    except CommandExecutionError as e:
        return PixiewpsResult(
            success=False,
            pin=None,
            duration_seconds=e.result.duration_seconds if hasattr(e, 'result') else 0.0,
            stdout=e.result.stdout if hasattr(e, 'result') else "",
            stderr=e.result.stderr if hasattr(e, 'result') else "",
            error_message=f"pixiewps execution failed: {e}",
        )
    except Exception as e:
        return PixiewpsResult(
            success=False,
            pin=None,
            duration_seconds=0.0,
            stdout="",
            stderr="",
            error_message=f"Unexpected error: {e}",
        )
    
    # Parse output for PIN
    pin = None
    pin_match = _PIN_RE.search(result.stdout)
    if pin_match:
        pin = pin_match.group(1)
    
    # Determine success (pin found or explicit success message)
    success = (
        pin is not None
        or "WPS pin:  " in result.stdout
        or result.returncode == 0
    )
    
    return PixiewpsResult(
        success=success,
        pin=pin,
        duration_seconds=result.duration_seconds,
        stdout=result.stdout,
        stderr=result.stderr,
        error_message=None if success else "No PIN recovered",
    )


def parameters_from_dict(data: dict[str, str]) -> PixiewpsParameters:
    """Construct PixiewpsParameters from dictionary.
    
    Args:
        data: Dictionary with keys: pke, pkr, e_hash1, e_hash2, authkey, e_nonce
    
    Returns:
        PixiewpsParameters instance
    
    Raises:
        KeyError: If required key is missing
    """
    return PixiewpsParameters(
        pke=data["pke"],
        pkr=data["pkr"],
        e_hash1=data["e_hash1"],
        e_hash2=data["e_hash2"],
        authkey=data["authkey"],
        e_nonce=data["e_nonce"],
    )
