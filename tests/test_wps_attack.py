"""Tests for wps_attack module."""

import pytest
from wifit_core.wps_attack import PixieData, AttackProgress
from wifit_core.models import AttackMethod, AttackOutcome


def test_pixie_data_initialization():
    """Test PixieData initialization."""
    data = PixieData()
    assert data.pke == ""
    assert data.pkr == ""
    assert not data.is_complete()


def test_pixie_data_complete():
    """Test PixieData completeness check."""
    data = PixieData(
        pke="A" * 192,
        pkr="B" * 192,
        e_hash1="C" * 64,
        e_hash2="D" * 64,
        authkey="E" * 64,
        e_nonce="F" * 32,
    )
    assert data.is_complete()


def test_pixie_data_clear():
    """Test PixieData clear method."""
    data = PixieData(pke="test", pkr="test")
    data.clear()
    assert data.pke == ""
    assert data.pkr == ""


def test_attack_progress_initialization():
    """Test AttackProgress initialization."""
    progress = AttackProgress()
    assert progress.last_m_message == 0
    assert progress.essid == ""
    assert progress.attempts == 0
    assert not progress.first_half_valid()


def test_attack_progress_first_half_valid():
    """Test first half validity check."""
    progress = AttackProgress()
    progress.last_m_message = 5
    assert progress.first_half_valid()
    
    progress.last_m_message = 4
    assert not progress.first_half_valid()


def test_attack_progress_clear():
    """Test AttackProgress clear method."""
    progress = AttackProgress()
    progress.last_m_message = 5
    progress.essid = "TestNetwork"
    progress.clear()
    assert progress.last_m_message == 0
    assert progress.essid == ""
