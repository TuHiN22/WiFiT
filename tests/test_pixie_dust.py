"""Tests for pixie_dust module."""

import pytest
from wifit_core.pixie_dust import PixiewpsParameters, PixiewpsResult


def test_pixiewps_parameters_validation():
    """Test parameter validation."""
    params = PixiewpsParameters(
        pke="A" * 192,
        pkr="B" * 192,
        e_hash1="C" * 64,
        e_hash2="D" * 64,
        authkey="E" * 64,
        e_nonce="F" * 32,
    )

    errors = params.validate()
    assert len(errors) == 0, f"Valid params should have no errors, got: {errors}"


def test_pixiewps_parameters_validation_empty():
    """Test validation with empty parameters."""
    params = PixiewpsParameters(
        pke="",
        pkr="",
        e_hash1="",
        e_hash2="",
        authkey="",
        e_nonce="",
    )

    errors = params.validate()
    assert len(errors) == 6  # All 6 fields are empty


def test_pixiewps_parameters_validation_wrong_length():
    """Test validation with wrong lengths."""
    params = PixiewpsParameters(
        pke="A" * 100,  # Should be 192
        pkr="B" * 100,  # Should be 192
        e_hash1="C" * 32,  # Should be 64
        e_hash2="D" * 32,  # Should be 64
        authkey="E" * 32,  # Should be 64
        e_nonce="F" * 16,  # Should be 32
    )

    errors = params.validate()
    assert len(errors) == 6  # All fields have wrong length


def test_pixiewps_parameters_validation_non_hex():
    """Test validation with non-hex characters."""
    params = PixiewpsParameters(
        pke="ZZZZ" + "A" * 188,
        pkr="B" * 192,
        e_hash1="C" * 64,
        e_hash2="D" * 64,
        authkey="E" * 64,
        e_nonce="F" * 32,
    )

    errors = params.validate()
    assert any("non-hex" in err for err in errors)


def test_pixiewps_result_success():
    """Test successful pixiewps result."""
    result = PixiewpsResult(
        success=True,
        pin="12345670",
        duration_seconds=5.0,
        stdout="WPS pin:  12345670",
        stderr="",
    )

    assert result.success
    assert not result.failed
    assert result.pin == "12345670"


def test_pixiewps_result_failure():
    """Test failed pixiewps result."""
    result = PixiewpsResult(
        success=False,
        pin=None,
        duration_seconds=120.0,
        stdout="",
        stderr="",
        error_message="No PIN recovered",
    )

    assert not result.success
    assert result.failed
    assert result.pin is None
