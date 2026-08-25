"""
Tests for CTAPHID/CTAP2 protocol handling.
"""

import struct

import pytest
from unittest.mock import MagicMock
from pypicokey.exceptions import CommunicationError
from pypicokey.protocol.ctap import CTAPHID, CTAPHandler

from tests.fake_transport import FakeCtapTransport, frame_response


class ScriptedCtapTransport:
    """Replays a fixed sequence of raw packets to receive()."""

    def __init__(self, packets):
        self.packets = list(packets)
        self.sent = []

    def send(self, data):
        self.sent.append(bytes(data))

    def receive(self, timeout=None):
        if not self.packets:
            return b""
        return self.packets.pop(0)


def make_initialized_handler(packets, cid=0x11223344, nonce=b"\x01" * 8,
                             monkeypatch=None):
    if monkeypatch is not None:
        monkeypatch.setattr("os.urandom", lambda n: nonce)
    init_resp = frame_response(
        cid, CTAPHID.INIT, nonce + struct.pack(">I", cid) + b"\x02\x00\x08\x03"
    )
    transport = ScriptedCtapTransport([init_resp] + list(packets))
    handler = CTAPHandler(transport)
    assert handler.init_device() is True
    return handler

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

    def test_exchange_chunks_large_payload(self):
        """A 200-byte payload must be split into init + continuation packets."""
        transport = FakeCtapTransport()
        transport.cbor_handler = lambda payload: b"\x00" + b"\xa0"
        handler = CTAPHandler(transport)
        assert handler.init_device() is True

        payload = bytes(range(256))[:200]
        response = handler.send_cbor(0x04, payload[1:])

        # All sent packets must reassemble to the exact original payload
        cmd, reassembled = transport.requests[-1]
        assert cmd == CTAPHID.CBOR
        assert reassembled == b"\x04" + payload[1:]
        assert response == b"\x00\xa0"

        expected_packets = 1 + -(-(len(payload) - 57) // 59)
        # sent_packets[0] is the CTAPHID INIT handshake
        assert len(transport.sent_packets) - 1 == expected_packets

    def test_exchange_small_payload_single_packet(self):
        transport = FakeCtapTransport()
        handler = CTAPHandler(transport)
        handler.init_device()

        handler.send_cbor(0x04)

        cmd, reassembled = transport.requests[-1]
        assert reassembled == b"\x04"

    def test_exchange_response_reassembly(self):
        """Multi-packet responses are reassembled from continuation frames."""
        transport = FakeCtapTransport()
        big = b"\x00" + b"ABCD" * 30  # 121 bytes: needs a continuation packet
        transport.cbor_handler = lambda payload: big
        handler = CTAPHandler(transport)
        handler.init_device()

        response = handler.send_cbor(0x04)
        assert response == big

    def test_init_device_short_reply_returns_false(self):
        transport = MagicMock()
        transport.receive.return_value = b"\x41" * 18
        assert CTAPHandler(transport).init_device() is False

    def test_init_device_garbage_command_returns_false(self, monkeypatch):
        nonce = b"\x01" * 8
        monkeypatch.setattr("os.urandom", lambda n: nonce)
        bad = frame_response(0xFFFFFFFF, 0x03, nonce + b"\xFF" * 11)  # MSG, not INIT
        transport = MagicMock()
        transport.receive.return_value = bad
        assert CTAPHandler(transport).init_device() is False


class TestExchangeFrameValidation:
    """Continuation packets must be validated and control frames filtered."""

    def _big_response_packets(self, cid, payload):
        body = b"\x00" + payload
        first = struct.pack(">IBH", cid, CTAPHID.CBOR | 0x80, len(body))
        first = (first + body[:57]).ljust(64, b"\x00")[:64]
        return first, body[57:]

    def test_keepalive_interleaved_mid_message(self, monkeypatch):
        cid = 0x11223344
        payload = bytes(range(100))
        first, rest = self._big_response_packets(cid, payload)
        keepalive = (
            struct.pack(">IB", cid, CTAPHID.KEEPALIVE) + b"\x01"
        ).ljust(64, b"\x00")
        cont = CTAPHID.create_cont_packet(cid, 0, rest)

        handler = make_initialized_handler(
            [first, keepalive, cont], cid=cid, monkeypatch=monkeypatch
        )
        response = handler.send_cbor(0x04, b"\x99")
        assert response == b"\x00" + payload

    def test_wrong_cid_in_continuation_raises(self, monkeypatch):
        cid = 0x11223344
        payload = bytes(range(100))
        first, rest = self._big_response_packets(cid, payload)
        cont = CTAPHID.create_cont_packet(0xDEADBEEF, 0, rest)

        handler = make_initialized_handler(
            [first, cont], cid=cid, monkeypatch=monkeypatch
        )
        with pytest.raises(CommunicationError):
            handler.send_cbor(0x04, b"\x99")

    def test_out_of_order_sequence_raises(self, monkeypatch):
        cid = 0x11223344
        payload = bytes(range(100))
        first, rest = self._big_response_packets(cid, payload)
        cont = CTAPHID.create_cont_packet(cid, 3, rest)

        handler = make_initialized_handler(
            [first, cont], cid=cid, monkeypatch=monkeypatch
        )
        with pytest.raises(CommunicationError):
            handler.send_cbor(0x04, b"\x99")

    def test_error_frame_raises(self, monkeypatch):
        cid = 0x11223344
        payload = bytes(range(100))
        first, _ = self._big_response_packets(cid, payload)
        error = (
            struct.pack(">IB", cid, CTAPHID.ERROR) + b"\x05"
        ).ljust(64, b"\x00")

        handler = make_initialized_handler(
            [first, error], cid=cid, monkeypatch=monkeypatch
        )
        with pytest.raises(CommunicationError):
            handler.send_cbor(0x04, b"\x99")


class TestFirstFrameValidation:
    """The first received frame must go through the same filtering rules."""

    def test_keepalive_as_first_frame_is_skipped(self, monkeypatch):
        cid = 0x11223344
        body = b"\x00" + b"OK"
        first = struct.pack(
            ">IBH", cid, CTAPHID.CBOR | 0x80, len(body)
        ) + body.ljust(57, b"\x00")
        first = first[:64]
        keepalive = (
            struct.pack(">IB", cid, CTAPHID.KEEPALIVE) + b"\x02"
        ).ljust(64, b"\x00")

        handler = make_initialized_handler(
            [keepalive, first], cid=cid, monkeypatch=monkeypatch
        )
        assert handler.send_cbor(0x04, b"\x99") == b"\x00OK"

    def test_error_as_first_frame_raises(self, monkeypatch):
        cid = 0x11223344
        error = (
            struct.pack(">IB", cid, CTAPHID.ERROR) + b"\x02"
        ).ljust(64, b"\x00")

        handler = make_initialized_handler(
            [error], cid=cid, monkeypatch=monkeypatch
        )
        with pytest.raises(CommunicationError):
            handler.send_cbor(0x04, b"\x99")

    def test_wrong_command_echo_as_first_frame_raises(self, monkeypatch):
        cid = 0x11223344
        wrong = struct.pack(
            ">IBH", cid, (CTAPHID.MSG | 0x80) & 0xFF, 2
        ) + b"\x00hi".ljust(59, b"\x00")
        wrong = wrong[:64]

        handler = make_initialized_handler(
            [wrong], cid=cid, monkeypatch=monkeypatch
        )
        with pytest.raises(CommunicationError):
            handler.send_cbor(0x04, b"\x99")

    def test_wrong_cid_on_first_frame_raises(self, monkeypatch):
        cid = 0x11223344
        body = b"\x00\x01"
        other = (
            struct.pack(">IBH", 0xDEADBEEF, CTAPHID.CBOR | 0x80, len(body))
            + body.ljust(59, b"\x00")
        )[:64]

        handler = make_initialized_handler(
            [other], cid=cid, monkeypatch=monkeypatch
        )
        with pytest.raises(CommunicationError):
            handler.send_cbor(0x04, b"\x99")

    def test_no_response_raises_communication_error(self, monkeypatch):
        cid = 0x11223344
        handler = make_initialized_handler([], cid=cid, monkeypatch=monkeypatch)
        with pytest.raises(CommunicationError):
            handler.send_cbor(0x04, b"\x99")
