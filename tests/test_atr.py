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
