"""
OpenPGP APDU builder and response parser for pypicokey.

This module provides helpers for constructing OpenPGP specific APDUs
and parsing TLV (Tag-Length-Value) responses.
"""

import struct
from typing import Optional, Dict, Any, List

class OpenPGPAPDU:
    """Helper for constructing OpenPGP command APDUs."""
    
    @staticmethod
    def select_application() -> bytes:
        """Select OpenPGP application."""
        # CLA: 00, INS: A4, P1: 04, P2: 00, Lc: 06, Data: D27600012401
        return bytes.fromhex("00A4040006D2760001240100")

    @staticmethod
    def get_data(tag: int) -> bytes:
        """Construct GET DATA APDU.
        
        Args:
            tag: 2-byte tag identifier (e.g. 0x004F for AID).
        """
        return struct.pack(">BBBB B H B", 0x00, 0xCA, tag >> 8, tag & 0xFF, 0x02, tag, 0x00)

    @staticmethod
    def verify_pin(pin: str, admin: bool = False) -> bytes:
        """Construct VERIFY PIN APDU.
        
        Args:
            pin: The PIN string.
            admin: If True, verify PW3 (admin); otherwise PW1 (user).
        """
        p2 = 0x83 if admin else 0x81
        pin_bytes = pin.encode("utf-8")
        return bytes([0x00, 0x20, 0x00, p2, len(pin_bytes)]) + pin_bytes


class TLVParser:
    """Parser for Tag-Length-Value (BER-TLV) encoded data."""
    
    @staticmethod
    def parse(data: bytes) -> Dict[int, bytes]:
        """Parse raw bytes into a dictionary of tags and values."""
        results = {}
        idx = 0
        while idx < len(data):
            # Parse Tag
            tag = data[idx]
            idx += 1
            if (tag & 0x1F) == 0x1F: # Multibyte tag
                tag = (tag << 8) | data[idx]
                idx += 1
            
            if idx >= len(data): break
            
            # Parse Length
            length = data[idx]
            idx += 1
            if length == 0x81:
                length = data[idx]
                idx += 1
            elif length == 0x82:
                length = (data[idx] << 8) | data[idx+1]
                idx += 2
            
            # Extract Value
            value = data[idx:idx+length]
            results[tag] = value
            idx += length
            
        return results
