"""
Tests for the CCID transport (status word chaining).
"""

import pytest

from pypicokey.exceptions import CommunicationError
from pypicokey.transport.ccid import CCIDTransport


def make_transport(side_effect):
    transport = CCIDTransport("fake-reader")
    transport._is_open = True
    transport._connection = type(
        "FakeConnection", (), {"transmit": staticmethod(side_effect)}
    )()
    return transport


class TestSendApdu:
    def test_normal_response(self):
        transport = make_transport(lambda apdu: ([0x01, 0x02], 0x90, 0x00))
        resp, sw1, sw2 = transport.send_apdu(0x00, 0xCA, 0x00, 0x4F, le=0)
        assert resp == b"\x01\x02"
        assert (sw1, sw2) == (0x90, 0x00)

    def test_sw61_get_response_chaining(self):
        calls = []

        def transmit(apdu):
            calls.append(list(apdu))
            if apdu[1] == 0xCA:
                return ([0x70, 0x61, 0x72, 0x74, 0x31], 0x61, 0x04)
            assert apdu == [0x00, 0xC0, 0x00, 0x00, 0x04]
            return ([0x70, 0x61, 0x72, 0x74], 0x90, 0x00)

        transport = make_transport(transmit)
        resp, sw1, sw2 = transport.send_apdu(0x00, 0xCA, 0x00, 0x4F, le=0)

        assert resp == b"part1part"
        assert (sw1, sw2) == (0x90, 0x00)
        assert len(calls) == 2

    def test_sw61_multiple_rounds(self):
        state = {"n": 0}

        def transmit(apdu):
            if apdu[1] != 0xC0:
                return ([0x78], 0x61, 0x01)
            state["n"] += 1
            if state["n"] < 3:
                return ([0x79], 0x61, 0x01)
            return ([0x79], 0x90, 0x00)

        transport = make_transport(transmit)
        resp, sw1, sw2 = transport.send_apdu(0x00, 0xCA, 0x00, 0x00, le=0)
        assert resp == b"xyyy"
        assert state["n"] == 3

    def test_sw6c_resend_with_correct_le(self):
        calls = []

        def transmit(apdu):
            calls.append(list(apdu))
            if len(calls) == 1:
                return ([], 0x6C, 0x10)
            return ([0x7A] * 16, 0x90, 0x00)

        transport = make_transport(transmit)
        resp, sw1, sw2 = transport.send_apdu(0x00, 0xCA, 0x00, 0x00, le=0)

        assert resp == b"z" * 16
        # Second attempt must use Le=0x10 as requested by the card
        assert calls[1][-1] == 0x10

    def test_sw6c_case3_apdu_data_not_corrupted(self):
        """Case-3 APDU (data, no Le): 6Cxx must append Le, not overwrite data."""
        calls = []

        def transmit(apdu):
            calls.append(list(apdu))
            if len(calls) == 1:
                return ([], 0x6C, 0x08)
            return ([], 0x90, 0x00)

        transport = make_transport(transmit)
        data = b"\xAA" * 8
        _, sw1, sw2 = transport.send_apdu(0x00, 0x24, 0x00, 0x81, data=data)

        resent = calls[1]
        # Header + Lc + untouched data + appended Le
        assert resent[:5] == [0x00, 0x24, 0x00, 0x81, len(data)]
        assert resent[5:-1] == list(data)
        assert resent[-1] == 0x08
        assert len(resent) == 14

    def test_sw61_zero_le_sends_p3_0x00(self):
        """SW 61 00 means 256 bytes remain; T=0 encodes that as P3/Le=0x00."""
        calls = []

        def transmit(apdu):
            calls.append(list(apdu))
            if apdu[1] != 0xC0:
                return ([], 0x61, 0x00)
            return ([0x42] * 4, 0x90, 0x00)

        transport = make_transport(transmit)
        resp, sw1, sw2 = transport.send_apdu(0x00, 0xCA, 0x00, 0x00, le=0)

        assert (sw1, sw2) == (0x90, 0x00)
        get_resp = calls[1]
        assert get_resp[:4] == [0x00, 0xC0, 0x00, 0x00]
        assert get_resp[4] == 0x00
        assert resp == b"\x42" * 4


class TestReceive:
    def test_receive_before_send_raises_cleanly(self):
        transport = CCIDTransport("fake-reader")
        transport._is_open = True
        transport._connection = object()
        with pytest.raises(CommunicationError):
            transport.receive()

    def test_receive_returns_last_response(self):
        transport = make_transport(lambda apdu: ([0x64, 0x61, 0x74, 0x61], 0x90, 0x00))
        transport.send(b"\x00\xca\x00\x4f\x00")
        assert transport.receive() == b"data\x90\x00"
