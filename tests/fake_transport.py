"""
Test helpers: in-memory fakes for CTAPHID and CCID transports.
"""

import struct
from unittest.mock import MagicMock

from pypicokey.constants import DeviceMode, ProductID, TransportType, VendorID
from pypicokey.device import DeviceInfo, PicoKeyDevice
from pypicokey.protocol.ctap import CTAPHID
from pypicokey.transport.ccid import CCIDTransport


def frame_response(cid: int, cmd: int, payload: bytes) -> bytes:
    """Frame a payload as a 64-byte CTAPHID init packet."""
    pkt = struct.pack(">IBH", cid, cmd | 0x80, len(payload)) + payload
    return pkt.ljust(CTAPHID.PACKET_SIZE, b"\x00")


class FakeCtapTransport:
    """In-memory transport speaking just enough CTAPHID for tests.

    Requests sent by the handler are reassembled into full messages
    (following the CTAPHID framing rules) and dispatched to handlers,
    whose replies are framed back to the caller.
    """

    def __init__(self, cid: int = 0x11223344) -> None:
        self.cid = cid
        self.sent_packets: list[bytes] = []
        self.requests: list[tuple[int, bytes]] = []
        self._pending: list[bytes] = []
        self.injected_responses: list[bytes] = []
        self.cbor_handler = None

    def send(self, data: bytes) -> None:
        self._pending.append(bytes(data))
        self.sent_packets.append(bytes(data))

    def receive(self, timeout=None) -> bytes:
        if self.injected_responses:
            return self.injected_responses.pop(0)
        if not self._pending:
            return b""
        first = self._pending.pop(0)
        cid, cmd, total_len = struct.unpack(">IBH", first[:7])
        message = bytearray(first[7:])
        seq = 0
        while len(message) < total_len and self._pending:
            cont = self._pending.pop(0)
            cont_cid, cont_seq = struct.unpack(">IB", cont[:5])
            if not cont_seq & 0x80 and not (cont_cid == cid and cont_seq == seq):
                raise AssertionError(
                    f"CTAPHID continuation mismatch: expected cid={cid:08X} "
                    f"seq={seq}, got cid={cont_cid:08X} byte={cont_seq}"
                )
            if not cont_seq & 0x80:
                seq += 1
            message += cont[5:]
        payload = bytes(message[:total_len])
        self.requests.append((cmd & 0x7F, payload))

        base_cmd = cmd & 0x7F
        if base_cmd == CTAPHID.INIT:
            nonce = payload[:8]
            resp_payload = (
                nonce
                + struct.pack(">I", self.cid)
                + bytes([0x02, 0x00])  # version 2.0
                + bytes([0x08])        # interface flags
                + bytes([0x03])        # capabilities (wink, CBOR)
            )
            return frame_response(cid, CTAPHID.INIT, resp_payload)

        if base_cmd == CTAPHID.CBOR:
            result = b"\x00" if self.cbor_handler is None else self.cbor_handler(payload)
            return frame_response(cid, CTAPHID.CBOR, result)

        return frame_response(cid, base_cmd, b"")


class ScriptedCcid(CCIDTransport):
    """CCID transport with scripted APDU responses (no hardware needed)."""

    def __init__(self, responder=None) -> None:
        super().__init__("fake-reader")
        self._is_open = True
        self._connection = MagicMock()
        self.apdus: list[tuple] = []
        self.responder = responder or (lambda *args: (b"", 0x90, 0x00))

    def send_apdu(self, cla, ins, p1, p2, data=None, le=None):
        self.apdus.append((cla, ins, p1, p2, data, le))
        return self.responder(cla, ins, p1, p2, data, le)


def make_device(mode: DeviceMode, transport=None) -> PicoKeyDevice:
    """Create a connected PicoKeyDevice (mock transport by default)."""
    info = DeviceInfo(
        vendor_id=VendorID.PICOKEYS,
        product_id=ProductID.UNKNOWN,
        name="Test Key",
        mode=mode,
    )
    device = PicoKeyDevice(info)
    device._transport = transport if transport is not None else MagicMock()
    device._connected = True
    return device


def make_ccid_device(mode: DeviceMode, responder=None):
    """Create a connected PicoKeyDevice with a ScriptedCcid transport."""
    info = DeviceInfo(
        vendor_id=VendorID.PICOKEYS,
        product_id=ProductID.UNKNOWN,
        name="Test Key",
        mode=mode,
        transport_type=TransportType.CCID,
    )
    device = PicoKeyDevice(info)
    device._transport = ScriptedCcid(responder)
    device._connected = True
    return device
