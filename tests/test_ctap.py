"""
Tests for CTAPHID/CTAP2 protocol handling.
"""

import pytest
from unittest.mock import MagicMock
from pypicokey.protocol.ctap import CTAPHID, CTAPHandler

class TestCTAPHID:
    def test_create_init_packet(self):
        cid = 0x12345678
        cmd = 0x06 # INIT
        payload = b"testdata"
        packet = CTAPHID.create_init_packet(cid, cmd, payload)
        
        assert len(packet) == 64
        assert packet[:4] == b"\x12\x34\x56\x78"
        assert packet[4] == 0x86 # cmd | 0x80
        assert packet[5:7] == b"\x00\x08" # len 8
        assert packet[7:15] == b"testdata"

    def test_create_cont_packet(self):
        cid = 0x12345678
        seq = 1
        payload = b"moredata"
        packet = CTAPHID.create_cont_packet(cid, seq, payload)
        
        assert len(packet) == 64
        assert packet[:4] == b"\x12\x34\x56\x78"
        assert packet[4] == 0x01 # seq
        assert packet[5:13] == b"moredata"

class TestCTAPHandler:
    def test_init_device_success(self, monkeypatch):
        transport = MagicMock()
        # Mock successful INIT response: CID 0xFFFFFFFF, CMD 0x86, LEN 17, Nonce (8), CID (4), ...
        nonce = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        monkeypatch.setattr("os.urandom", lambda n: nonce)
        
        resp_payload = nonce + b"\x11\x22\x33\x44\x02\x00\x01" # Nonce + CID + Protocol version...
        resp_packet = b"\xFF\xFF\xFF\xFF\x86\x00\x11" + resp_payload
        resp_packet = resp_packet.ljust(64, b"\x00")
        
        transport.receive.return_value = resp_packet
        
        handler = CTAPHandler(transport)
        assert handler.init_device() is True
        assert handler._cid == 0x11223344
