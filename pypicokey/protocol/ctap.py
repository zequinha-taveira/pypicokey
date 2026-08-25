"""
CTAP (Client to Authenticator Protocol) implementation for pypicokey.

This module provides CTAPHID framing and CTAP2 command handling.
"""

import struct
import os
import logging
from typing import Optional

from pypicokey.exceptions import CommunicationError

logger = logging.getLogger(__name__)


class CTAPHID:
    """CTAPHID protocol constants and framing."""
    
    # Commands
    MSG = 0x03
    CBOR = 0x10
    INIT = 0x06
    PING = 0x01
    ERROR = 0x3F
    KEEPALIVE = 0x3B
    
    # Packet types
    TYPE_INIT = 0x80
    TYPE_CONT = 0x00
    
    # Broadcast channel
    BROADCAST_CID = 0xFFFFFFFF
    
    # Packet sizes
    PACKET_SIZE = 64
    INIT_HEADER_SIZE = 7
    CONT_HEADER_SIZE = 5
    
    @staticmethod
    def create_init_packet(
        cid: int,
        cmd: int,
        payload: bytes,
        total_len: Optional[int] = None,
    ) -> bytes:
        """Create an initial CTAPHID packet.
        
        Args:
            cid: Channel ID.
            cmd: Command byte.
            payload: Data payload (first chunk of the message).
            total_len: Total message length for the LEN field. Defaults to
                len(payload) for single-packet messages.
            
        Returns:
            64-byte packet.
        """
        length = len(payload) if total_len is None else total_len
        header = struct.pack(">IBH", cid, cmd | 0x80, length)
        packet = header + payload
        return packet.ljust(CTAPHID.PACKET_SIZE, b"\x00")[:CTAPHID.PACKET_SIZE]

    @staticmethod
    def create_cont_packet(cid: int, seq: int, payload: bytes) -> bytes:
        """Create a continuation CTAPHID packet.
        
        Args:
            cid: Channel ID.
            seq: Sequence number (0-127).
            payload: Data payload.
            
        Returns:
            64-byte packet.
        """
        header = struct.pack(">IB", cid, seq & 0x7F)
        packet = header + payload
        return packet.ljust(CTAPHID.PACKET_SIZE, b"\x00")[:CTAPHID.PACKET_SIZE]


class CTAPHandler:
    """Handles CTAPHID communication with a device."""
    
    def __init__(self, transport) -> None:
        self._transport = transport
        self._cid = CTAPHID.BROADCAST_CID

    def init_device(self) -> bool:
        """Initialize CTAPHID and get a channel ID."""
        nonce = os.urandom(8)
        packet = CTAPHID.create_init_packet(self._cid, CTAPHID.INIT, nonce)

        self._transport.send(packet)
        response = self._transport.receive()

        if not response or len(response) < 19:
            return False

        # Verify nonce
        resp_cid, resp_cmd, resp_len = struct.unpack(">IBH", response[:7])
        resp_nonce = response[7:15]

        if resp_cmd != (CTAPHID.INIT | 0x80):
            logger.error(f"CTAPHID INIT: unexpected command 0x{resp_cmd:02X}")
            return False

        if resp_nonce != nonce:
            logger.error("CTAPHID INIT: Nonce mismatch")
            return False

        # New CID is in the payload after the nonce
        self._cid = struct.unpack(">I", response[15:19])[0]
        logger.debug(f"CTAPHID initialized. New CID: {self._cid:08X}")
        return True

    def send_cbor(self, ctap_cmd: int, data: bytes = b"") -> bytes:
        """Send a CTAP2 CBOR command and receive the response.
        
        Args:
            ctap_cmd: Command byte (e.g., 0x04 for getInfo).
            data: CBOR encoded parameters.
            
        Returns:
            CBOR encoded response.
        """
        payload = bytes([ctap_cmd]) + data
        return self._exchange(CTAPHID.CBOR, payload)

    def _exchange(self, cmd: int, payload: bytes) -> bytes:
        """Send a full CTAPHID message and collect the response."""
        # Sending
        remaining = payload
        
        # Init packet
        chunk = remaining[:CTAPHID.PACKET_SIZE - CTAPHID.INIT_HEADER_SIZE]
        self._transport.send(CTAPHID.create_init_packet(
            self._cid, cmd, chunk, total_len=len(payload)
        ))
        remaining = remaining[len(chunk):]
        
        # Cont packets
        seq = 0
        while remaining:
            chunk = remaining[:CTAPHID.PACKET_SIZE - CTAPHID.CONT_HEADER_SIZE]
            self._transport.send(CTAPHID.create_cont_packet(self._cid, seq, chunk))
            remaining = remaining[len(chunk):]
            seq += 1

        # Receiving
        message = b""
        expected_seq = 0
        total_len: int | None = None

        while total_len is None or len(message) < total_len:
            response = self._transport.receive()
            if not response:
                if total_len is None:
                    raise CommunicationError("No response from device")
                break

            resp_cid, resp_cmd, resp_len = struct.unpack(">IBH", response[:7])

            if resp_cmd == CTAPHID.KEEPALIVE:
                continue
            if resp_cmd == CTAPHID.ERROR:
                raise CommunicationError(
                    f"Device reported CTAPHID ERROR (status 0x{response[5]:02X})"
                )
            if resp_cid != self._cid:
                raise CommunicationError(
                    f"CID mismatch: expected {self._cid:08X}, got {resp_cid:08X}"
                )

            if total_len is None:
                if resp_cmd != (cmd | 0x80):
                    raise CommunicationError(
                        f"Unexpected CTAPHID command: expected "
                        f"0x{cmd | 0x80:02X}, got 0x{resp_cmd:02X}"
                    )
                total_len = resp_len
                message += response[7:]
            else:
                if resp_cmd != expected_seq:
                    raise CommunicationError(
                        f"Out-of-order continuation packet: expected seq "
                        f"{expected_seq}, got {resp_cmd}"
                    )
                expected_seq += 1
                message += response[5:]

        return message[:total_len] if total_len is not None else b""
