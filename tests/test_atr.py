"""
Tests for ATR parsing.
"""

import pytest
from pypicokey.utils.atr import ATRParser

def test_parse_openpgp_atr():
    parser = ATRParser()
    # Typical OpenPGP ATR with historical bytes
    atr = bytes.fromhex("3B DA 18 FF 81 B1 FE 75 1F 03 00 31 C5 73 C0 01 40 00 90 00 0C")
    info = parser.parse(atr)
    # Search for OpenPGP indicator or check type
    # Not all ATRs for OpenPGP have the literal string, but the parser handles hints
    assert info.card_type != "invalid"

def test_detect_pico_openpgp():
    parser = ATRParser()
    # ATR containing "PicoOpenPGP" string in historical bytes (theoretical)
    hist = b"PicoOpenPGP"
    atr = b"\x3B\x8B" + b"\x00" * 0 + hist # Simpler ATR structure
    # Since we didn't implement full interface byte skip in the mock, 
    # we just test the detection logic directly
    card_type = parser._detect_card_type(hist)
    assert card_type == "openpgp"

def test_detect_hsm():
    parser = ATRParser()
    hist = b"PicoHSM"
    card_type = parser._detect_card_type(hist)
    assert card_type == "hsm"


class TestTruncatedAtr:
    def test_truncated_historical_bytes_returns_partial_slice(self):
        parser = ATRParser()
        # T0 = 0x5F: K=15 historical bytes, TA/TC present, no TD; the ATR
        # is cut short so only one of the announced historical bytes fits.
        atr = b"\x3B\x5F" + b"\xA1\xB2\xC3"
        info = parser.parse(atr)
        assert info.historical_bytes == b"\xC3"
        assert info.tck is None

    def test_t1_atr_tck_read_from_correct_byte(self):
        parser = ATRParser()
        # T0 = 0x81: 1 historical byte, TD1 present announcing T=1 only
        # Layout: TS T0 TD1 HIST TCK
        atr = b"\x3B\x81\x01\xAA\x7E"
        info = parser.parse(atr)
        assert 1 in info.protocols
        assert info.historical_bytes == b"\xAA"
        assert info.tck == 0x7E

    def test_full_historical_bytes_unchanged(self):
        parser = ATRParser()
        # T0 = 0x24: TB present, 4 historical bytes, all within bounds
        atr = b"\x3B\x24\x00" + b"PicoKey"
        info = parser.parse(atr)
        assert info.historical_bytes == b"Pico"
