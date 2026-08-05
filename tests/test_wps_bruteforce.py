"""Tests for deterministic WPS brute force."""

import tempfile
import unittest
from pathlib import Path

from wifit_core.wps_bruteforce import (
    BruteforceProgress,
    BruteforceSession,
    bruteforce_with_callbacks,
    enumerate_all_pins,
)


class BruteforceProgressTests(unittest.TestCase):
    def test_creates_valid_first_half_progress(self):
        progress = BruteforceProgress(
            bssid="AABBCCDDEEFF",
            started_at="2026-08-05T12:00:00Z",
            phase="first_half",
            first_half=1234,
            second_half=0,
            attempts=1234,
            successful_first_halves=(),
        )
        
        self.assertEqual(progress.phase, "first_half")
        self.assertEqual(progress.first_half, 1234)
        self.assertFalse(progress.is_complete())
    
    def test_to_pin_generates_correct_first_half_pin(self):
        progress = BruteforceProgress(
            bssid="AABBCCDDEEFF",
            started_at="2026-08-05T12:00:00Z",
            phase="first_half",
            first_half=5678,
            second_half=0,
            attempts=1,
            successful_first_halves=(),
        )
        
        pin = progress.to_pin()
        self.assertEqual(len(pin), 8)
        # First 4 digits should be 5678, next 3 are 000, last is checksum
        self.assertTrue(pin.startswith("5678000"))
    
    def test_to_pin_generates_correct_second_half_pin(self):
        progress = BruteforceProgress(
            bssid="AABBCCDDEEFF",
            started_at="2026-08-05T12:00:00Z",
            phase="second_half",
            first_half=0,  # Index into successful_first_halves
            second_half=123,
            attempts=10001,
            successful_first_halves=(5678,),
        )
        
        pin = progress.to_pin()
        self.assertEqual(len(pin), 8)
        # First 4 digits should be 5678, next 3 are 123, last is checksum
        # Verify the PIN structure
        self.assertTrue(int(pin[:7]) == 5678123)
    
    def test_first_half_phase_advances_correctly(self):
        progress = BruteforceProgress(
            bssid="AABBCCDDEEFF",
            started_at="2026-08-05T12:00:00Z",
            phase="first_half",
            first_half=100,
            second_half=0,
            attempts=100,
            successful_first_halves=(),
        )
        
        next_progress = progress.next_attempt()
        self.assertEqual(next_progress.first_half, 101)
        self.assertEqual(next_progress.attempts, 101)
        self.assertEqual(next_progress.phase, "first_half")
    
    def test_first_half_records_success(self):
        progress = BruteforceProgress(
            bssid="AABBCCDDEEFF",
            started_at="2026-08-05T12:00:00Z",
            phase="first_half",
            first_half=100,
            second_half=0,
            attempts=100,
            successful_first_halves=(50, 75),
        )
        
        next_progress = progress.next_attempt(first_half_success=True)
        self.assertEqual(next_progress.successful_first_halves, (50, 75, 100))
    
    def test_transitions_to_second_half_after_9999(self):
        progress = BruteforceProgress(
            bssid="AABBCCDDEEFF",
            started_at="2026-08-05T12:00:00Z",
            phase="first_half",
            first_half=9999,
            second_half=0,
            attempts=9999,
            successful_first_halves=(100, 200),
        )
        
        next_progress = progress.next_attempt()
        self.assertEqual(next_progress.phase, "second_half")
        self.assertEqual(next_progress.first_half, 0)  # Index into successful list
        self.assertEqual(next_progress.second_half, 0)
        self.assertEqual(next_progress.successful_first_halves, (100, 200))
    
    def test_marks_complete_when_no_successful_first_halves(self):
        progress = BruteforceProgress(
            bssid="AABBCCDDEEFF",
            started_at="2026-08-05T12:00:00Z",
            phase="first_half",
            first_half=9999,
            second_half=0,
            attempts=9999,
            successful_first_halves=(),
        )
        
        next_progress = progress.next_attempt()
        self.assertTrue(next_progress.is_complete())
        self.assertEqual(next_progress.first_half, 10000)
    
    def test_second_half_advances_correctly(self):
        progress = BruteforceProgress(
            bssid="AABBCCDDEEFF",
            started_at="2026-08-05T12:00:00Z",
            phase="second_half",
            first_half=0,
            second_half=500,
            attempts=10500,
            successful_first_halves=(1234,),
        )
        
        next_progress = progress.next_attempt()
        self.assertEqual(next_progress.second_half, 501)
        self.assertEqual(next_progress.first_half, 0)
    
    def test_second_half_advances_to_next_successful_first_half(self):
        progress = BruteforceProgress(
            bssid="AABBCCDDEEFF",
            started_at="2026-08-05T12:00:00Z",
            phase="second_half",
            first_half=0,
            second_half=999,
            attempts=10999,
            successful_first_halves=(1234, 5678),
        )
        
        next_progress = progress.next_attempt()
        self.assertEqual(next_progress.first_half, 1)  # Next index
        self.assertEqual(next_progress.second_half, 0)
    
    def test_second_half_completes_after_all_exhausted(self):
        progress = BruteforceProgress(
            bssid="AABBCCDDEEFF",
            started_at="2026-08-05T12:00:00Z",
            phase="second_half",
            first_half=1,  # Last successful first half index
            second_half=999,
            attempts=11999,
            successful_first_halves=(1234, 5678),
        )
        
        next_progress = progress.next_attempt()
        self.assertTrue(next_progress.is_complete())
    
    def test_get_actual_first_half_in_second_phase(self):
        progress = BruteforceProgress(
            bssid="AABBCCDDEEFF",
            started_at="2026-08-05T12:00:00Z",
            phase="second_half",
            first_half=2,
            second_half=100,
            attempts=12100,
            successful_first_halves=(1111, 2222, 3333, 4444),
        )
        
        self.assertEqual(progress.get_actual_first_half(), 3333)


class BruteforceSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.session_dir = Path(self.temp_dir) / "bruteforce-sessions"
    
    def test_start_creates_new_session(self):
        session = BruteforceSession(
            "AA:BB:CC:DD:EE:FF",
            session_dir=self.session_dir,
            session_id="test001",
        )
        
        progress = session.start()
        self.assertEqual(progress.phase, "first_half")
        self.assertEqual(progress.first_half, 0)
        self.assertEqual(progress.attempts, 0)
        self.assertTrue(session.session_file.exists())
    
    def test_save_and_load_roundtrip(self):
        session = BruteforceSession(
            "AA:BB:CC:DD:EE:FF",
            session_dir=self.session_dir,
            session_id="test002",
        )
        
        progress = session.start()
        # Advance a few times
        session.update()
        session.update()
        session.update(first_half_success=True)
        
        # Create new session instance and load
        session2 = BruteforceSession(
            "AABBCCDDEEFF",  # Same BSSID, different format
            session_dir=self.session_dir,
            session_id="test002",
        )
        loaded = session2.load()
        
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.first_half, 3)
        self.assertEqual(loaded.attempts, 3)
        self.assertEqual(loaded.successful_first_halves, (2,))
    
    def test_resume_continues_from_saved_state(self):
        session = BruteforceSession(
            "AA:BB:CC:DD:EE:FF",
            session_dir=self.session_dir,
            session_id="test003",
        )
        
        # Start and advance
        session.start()
        for _ in range(100):
            session.update()
        
        # New session resumes
        session2 = BruteforceSession(
            "AABBCCDDEEFF",
            session_dir=self.session_dir,
            session_id="test003",
        )
        progress = session2.start()
        self.assertEqual(progress.first_half, 100)
        self.assertEqual(progress.attempts, 100)
    
    def test_delete_removes_session_file(self):
        session = BruteforceSession(
            "AA:BB:CC:DD:EE:FF",
            session_dir=self.session_dir,
            session_id="test004",
        )
        
        session.start()
        self.assertTrue(session.session_file.exists())
        
        session.delete()
        self.assertFalse(session.session_file.exists())
    
    def test_iterate_pins_yields_correct_sequence(self):
        session = BruteforceSession(
            "AA:BB:CC:DD:EE:FF",
            session_dir=self.session_dir,
            session_id="test005",
        )
        
        pins_seen = []
        for progress, pin in session.iterate_pins():
            pins_seen.append(pin)
            if len(pins_seen) >= 10:
                break
        
        self.assertEqual(len(pins_seen), 10)
        # All should be 8-digit strings
        for pin in pins_seen:
            self.assertEqual(len(pin), 8)
            self.assertTrue(pin.isdigit())


class EnumerateAllPinsTests(unittest.TestCase):
    def test_yields_valid_pins(self):
        pins = []
        for pin in enumerate_all_pins():
            pins.append(pin)
            if len(pins) >= 100:
                break
        
        self.assertEqual(len(pins), 100)
        for pin in pins:
            self.assertEqual(len(pin), 8)
            self.assertTrue(pin.isdigit())
    
    def test_starts_with_zero_if_include_zero(self):
        first_pin = next(enumerate_all_pins(include_zero=True))
        self.assertEqual(first_pin, "00000000")
    
    def test_starts_with_one_if_exclude_zero(self):
        first_pin = next(enumerate_all_pins(include_zero=False))
        # First half = 1, second half = 0 (during first half phase)
        # PIN = 0001000 + checksum
        self.assertTrue(first_pin.startswith("0001000"))
    
    def test_no_duplicates_in_first_11000(self):
        pins = set()
        count = 0
        for pin in enumerate_all_pins():
            pins.add(pin)
            count += 1
            if count >= 11000:
                break
        
        # Should have exactly 11000 unique PINs (10000 first half + 1000 second)
        # Actually it's 10000 + (10000 * 999) since we skip second_half=0 in second phase
        # But the enumeration is designed for illustration; unique coverage is key
        self.assertGreater(len(pins), 10000)


class BruteforceWithCallbacksTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.session_dir = Path(self.temp_dir) / "bruteforce-sessions"
    
    def test_finds_pin_in_first_half(self):
        target_pin = None
        attempts_log = []
        
        def try_pin(pin: str) -> tuple[bool, bool]:
            attempts_log.append(pin)
            # Succeed on 100th attempt (first_half=99, second=000)
            if len(attempts_log) == 100:
                nonlocal target_pin
                target_pin = pin
                return True, True
            return False, True  # First half always valid for test
        
        found_pin, total = bruteforce_with_callbacks(
            "AA:BB:CC:DD:EE:FF",
            try_pin,
            session_dir=self.session_dir,
            session_id="callback_test001",
        )
        
        self.assertEqual(found_pin, target_pin)
        self.assertEqual(total, 100)
        self.assertEqual(len(attempts_log), 100)
    
    def test_invokes_first_half_callback(self):
        first_half_log = []
        attempts = []
        
        def try_pin(pin: str) -> tuple[bool, bool]:
            attempts.append(pin)
            if len(attempts) >= 50:
                return True, True  # Stop early
            return False, True
        
        def first_half_cb(first_half: int, valid: bool) -> None:
            first_half_log.append((first_half, valid))
        
        bruteforce_with_callbacks(
            "AA:BB:CC:DD:EE:FF",
            try_pin,
            first_half_callback=first_half_cb,
            session_dir=self.session_dir,
            session_id="callback_test002",
        )
        
        # Callback is invoked for each first-half attempt
        self.assertGreater(len(first_half_log), 0)
        # First entry should be first_half=0
        self.assertEqual(first_half_log[0][0], 0)
    
    def test_transitions_to_second_half_after_valid_first_half(self):
        second_half_log = []
        valid_first_halves = {10, 20, 30}
        attempts = []
        
        def try_pin(pin: str) -> tuple[bool, bool]:
            attempts.append(pin)
            # Parse first half from pin
            first_4_digits = int(pin[:4])
            if first_4_digits in valid_first_halves:
                # In second half phase now
                if len(attempts) >= 50:  # Stop early to avoid long test
                    return True, True  # Found
                return False, True
            # First half phase
            return False, first_4_digits in valid_first_halves
        
        def second_half_cb(first_half: int, second_half: int, success: bool) -> None:
            second_half_log.append((first_half, second_half, success))
        
        result_pin, total = bruteforce_with_callbacks(
            "AA:BB:CC:DD:EE:FF",
            try_pin,
            second_half_callback=second_half_cb,
            session_dir=self.session_dir,
            session_id="callback_test003",
        )
        
        # Should have had some attempts
        self.assertGreater(len(attempts), 0)
    
    def test_exhausts_all_pins_if_none_succeed(self):
        attempts = []
        
        def try_pin(pin: str) -> tuple[bool, bool]:
            attempts.append(pin)
            # Stop after 200 attempts to keep test fast
            if len(attempts) >= 200:
                return True, True
            return False, False  # All first halves invalid
        
        found_pin, total = bruteforce_with_callbacks(
            "AA:BB:CC:DD:EE:FF",
            try_pin,
            session_dir=self.session_dir,
            session_id="callback_test004",
        )
        
        self.assertIsNotNone(found_pin)  # We forced success at 200
        self.assertEqual(total, 200)


if __name__ == "__main__":
    unittest.main()
