"""
OTP module for pypicokey.

This module provides OTP (One-Time Password) functionality for
interacting with Pico OTP devices, compatible with YubiKey OTP protocol.
"""

from typing import Optional
from dataclasses import dataclass
import logging
import hmac
import hashlib
import struct

from pypicokey.device import PicoKeyDevice
from pypicokey.constants import DeviceMode
from pypicokey.exceptions import UnsupportedModeError, CommunicationError, AuthenticationError

logger = logging.getLogger(__name__)


@dataclass
class OTPSlot:
    """OTP slot configuration."""
    
    slot: int  # 1 or 2
    enabled: bool
    touch_required: bool
    secret_present: bool
    public_id: Optional[str] = None
    private_id: Optional[bytes] = None
    access_code: Optional[bytes] = None


@dataclass
class HOTPInfo:
    """HOTP configuration information."""
    
    slot: int
    algorithm: str
    digits: int
    counter: int
    secret_set: bool


class OTPModule:
    """OTP operations for Pico OTP devices.
    
    Implements YubiKey-compatible OTP protocol and HOTP/SLOT commands.
    """
    
    # OTP Commands (YubiKey compatible)
    CMD_DEVICE_SERIAL = 0x01
    CMD_DEVICE_INFO = 0x02
    CMD_SLOT_STATUS = 0x04
    CMD_CONFIG_OTP = 0x01
    CMD_CONFIG_HOTP = 0x30
    CMD_CHALLENGE_OTP = 0x02
    CMD_CHALLENGE_HOTP = 0x30
    CMD_SWAP_SLOTS = 0x03
    CMD_WIPE_SLOT = 0x04
    
    # APDU Instructions for CCID transport
    INS_CONFIGURE = 0x01
    INS_CHALLENGE = 0x02
    INS_STATUS = 0x04
    INS_SERIAL = 0x10
    INS_HOTP = 0x30
    
    def __init__(self, device: PicoKeyDevice) -> None:
        """Initialize OTP module.
        
        Args:
            device: Connected PicoKeyDevice instance.
        """
        if device.mode != DeviceMode.OTP:
            raise UnsupportedModeError(
                "OTP module requires an OTP device",
                current_mode=str(device.mode),
                required_mode=str(DeviceMode.OTP),
            )
        
        self._device = device
        self._selected = False
    
    def _ensure_selected(self) -> None:
        """Ensure the OTP application is selected."""
        if not self._selected:
            self.select()
    
    def select(self) -> bool:
        """Select the OTP application.
        
        Returns:
            True if the application was selected (or selection is not needed).
            
        Raises:
            CommunicationError: If the device transport is CCID and the
                application cannot be selected.
        """
        from pypicokey.transport.ccid import CCIDTransport
        if not isinstance(self._device._transport, CCIDTransport):
            # For HID transport, we don't need to select
            self._selected = True
            return True
        
        try:
            # Try to select OTP application (vendor-specific AID)
            otp_aid = bytes.fromhex("A0000005272001")
            _, sw1, sw2 = self._device._transport.select_application(otp_aid)
            
            if sw1 == 0x90:
                self._selected = True
                return True
            
            raise CommunicationError(
                f"Failed to select OTP application: {sw1:02X}{sw2:02X}"
            )
        except CommunicationError:
            raise
        except Exception as e:
            raise CommunicationError(f"OTP selection failed: {e}") from e
    
    def get_serial(self) -> Optional[int]:
        """Get device serial number.
        
        Returns:
            Serial number as integer, or None if not available.
            
        Raises:
            CommunicationError: If command fails.
        """
        self._ensure_selected()
        
        try:
            # SERIAL command via APDU
            resp, sw1, sw2 = self._device._transport.send_apdu(
                0x00, self.INS_SERIAL, 0x00, 0x00, le=4
            )
            
            if sw1 == 0x90 and len(resp) >= 4:
                return struct.unpack(">I", resp[:4])[0]
            else:
                logger.debug(f"Serial not available: {sw1:02X}{sw2:02X}")
                return None
        except Exception as e:
            logger.debug(f"Could not get serial: {e}")
            return None
    
    def get_slot_status(self) -> tuple[bool, bool]:
        """Get status of both OTP slots.
        
        Returns:
            Tuple of (slot1_configured, slot2_configured).
            
        Raises:
            CommunicationError: If command fails.
        """
        self._ensure_selected()
        
        try:
            # SLOT STATUS command
            resp, sw1, sw2 = self._device._transport.send_apdu(
                0x00, self.INS_STATUS, 0x00, 0x00, le=1
            )
            
            if sw1 == 0x90 and len(resp) >= 1:
                status_byte = resp[0]
                slot1 = bool(status_byte & 0x01)
                slot2 = bool(status_byte & 0x02)
                return (slot1, slot2)
            else:
                return (False, False)
        except Exception as e:
            logger.debug(f"Could not get slot status: {e}")
            return (False, False)
    
    def configure_otp(
        self,
        slot: int,
        public_id: str,
        private_id: bytes,
        secret_key: bytes,
        access_code: Optional[bytes] = None,
        touch_required: bool = True,
    ) -> bool:
        """Configure an OTP slot with YubiKey-compatible credentials.
        
        Args:
            slot: Slot number (1 or 2).
            public_id: Public ID (6 characters, modhex encoded).
            private_id: Private ID (6 bytes).
            secret_key: AES key (16 bytes).
            access_code: Optional access code (6 bytes) for slot protection.
            touch_required: Whether touch is required for OTP generation.
            
        Returns:
            True if configuration was successful.
            
        Raises:
            ValueError: If parameters are invalid.
            CommunicationError: If command fails.
        """
        self._ensure_selected()
        
        if slot not in [1, 2]:
            raise ValueError("Slot must be 1 or 2")
        if len(private_id) != 6:
            raise ValueError("Private ID must be 6 bytes")
        if len(secret_key) != 16:
            raise ValueError("Secret key must be 16 bytes (AES-128)")
        if access_code and len(access_code) != 6:
            raise ValueError("Access code must be 6 bytes")
        
        try:
            # Build configuration payload
            # Format: [public_id (6)] [private_id (6)] [secret_key (16)] [flags] [access_code (6, optional)]
            public_bytes = public_id.encode('ascii') if isinstance(public_id, str) else public_id
            if len(public_bytes) > 6:
                public_bytes = public_bytes[:6]
            public_bytes = public_bytes.ljust(6, b'\x00')
            
            # Finalize flags first: touch bit + access-code bit
            flags = 0x01 if touch_required else 0x00
            if access_code:
                flags |= 0x80
            
            # Build configuration payload in device-expected order:
            # [public_id (6)] [private_id (6)] [secret_key (16)] [flags] [access_code (6)]
            payload = public_bytes + private_id + secret_key + bytes([flags])
            
            if access_code:
                payload += access_code
            
            # CONFIGURE OTP command
            p2 = slot - 1  # 0 for slot 1, 1 for slot 2
            _, sw1, sw2 = self._device._transport.send_apdu(
                0x00, self.INS_CONFIGURE, p2, 0x00, data=payload
            )
            
            if sw1 == 0x90:
                logger.info(f"Configured OTP slot {slot}")
                return True
            else:
                raise CommunicationError(f"OTP configuration failed: {sw1:02X}{sw2:02X}")
        except Exception as e:
            if not isinstance(e, (ValueError, CommunicationError)):
                raise CommunicationError(f"OTP config error: {e}") from e
            raise
    
    def configure_hotp(
        self,
        slot: int,
        secret_key: bytes,
        digits: int = 6,
        counter: int = 0,
        touch_required: bool = True,
    ) -> bool:
        """Configure an OTP slot for HOTP (RFC 4226).
        
        Args:
            slot: Slot number (1 or 2).
            secret_key: HMAC-SHA1 secret key.
            digits: Number of digits (6 or 8).
            counter: Initial counter value.
            touch_required: Whether touch is required.
            
        Returns:
            True if configuration was successful.
            
        Raises:
            ValueError: If parameters are invalid.
            CommunicationError: If command fails.
        """
        self._ensure_selected()
        
        if slot not in [1, 2]:
            raise ValueError("Slot must be 1 or 2")
        if len(secret_key) < 10 or len(secret_key) > 64:
            raise ValueError("Secret key must be 10-64 bytes")
        if digits not in [6, 8]:
            raise ValueError("Digits must be 6 or 8")
        
        try:
            # Build HOTP configuration payload
            flags = (digits - 6) << 4  # 0 for 6 digits, 16 for 8
            flags |= 0x01 if touch_required else 0x00
            
            counter_bytes = struct.pack(">Q", counter)
            
            payload = bytes([len(secret_key)]) + secret_key + counter_bytes + bytes([flags])
            
            # CONFIGURE HOTP command
            p2 = slot - 1
            _, sw1, sw2 = self._device._transport.send_apdu(
                0x00, self.INS_HOTP, p2, 0x00, data=payload
            )
            
            if sw1 == 0x90:
                logger.info(f"Configured HOTP slot {slot}")
                return True
            else:
                raise CommunicationError(f"HOTP configuration failed: {sw1:02X}{sw2:02X}")
        except Exception as e:
            if not isinstance(e, (ValueError, CommunicationError)):
                raise CommunicationError(f"HOTP config error: {e}") from e
            raise
    
    def generate_otp(self, slot: int, challenge: Optional[bytes] = None) -> str:
        """Generate OTP code from a slot.
        
        Args:
            slot: Slot number (1 or 2).
            challenge: Optional challenge for challenge-response.
            
        Returns:
            OTP code as string.
            
        Raises:
            ValueError: If slot is invalid.
            CommunicationError: If command fails.
        """
        self._ensure_selected()
        
        if slot not in [1, 2]:
            raise ValueError("Slot must be 1 or 2")
        
        try:
            if challenge:
                # Challenge-response mode
                resp, sw1, sw2 = self._device._transport.send_apdu(
                    0x00, self.INS_CHALLENGE, slot - 1, 0x00, data=challenge, le=0
                )
                
                if sw1 == 0x90:
                    return resp.hex().upper()
                else:
                    raise CommunicationError(f"Challenge failed: {sw1:02X}{sw2:02X}")
            else:
                # Standard OTP mode - device sends automatically on touch
                # This would typically be handled by HID keyboard emulation
                # For CCID, we request the current OTP
                resp, sw1, sw2 = self._device._transport.send_apdu(
                    0x00, self.INS_CHALLENGE, slot - 1, 0x01, le=0
                )
                
                if sw1 == 0x90:
                    # Decode OTP response
                    return resp.decode('ascii', errors='ignore')
                else:
                    raise CommunicationError(f"OTP generation failed: {sw1:02X}{sw2:02X}")
        except Exception as e:
            if not isinstance(e, (ValueError, CommunicationError)):
                raise CommunicationError(f"OTP generation error: {e}") from e
            raise
    
    def generate_hotp(self, slot: int) -> str:
        """Generate HOTP code from a slot.

        Args:
            slot: Slot number (1 or 2).

        Returns:
            HOTP code as string.

        Raises:
            ValueError: If slot is invalid.
            CommunicationError: If command fails.
        """
        self._ensure_selected()

        if slot not in [1, 2]:
            raise ValueError("Slot must be 1 or 2")

        try:
            resp, sw1, sw2 = self._device._transport.send_apdu(
                0x00, self.INS_HOTP, slot - 1, 0x00, le=0
            )

            if sw1 == 0x90:
                return resp.hex().upper()
            else:
                raise CommunicationError(f"HOTP generation failed: {sw1:02X}{sw2:02X}")
        except Exception as e:
            if not isinstance(e, (ValueError, CommunicationError)):
                raise CommunicationError(f"HOTP generation error: {e}") from e
            raise

    def swap_slots(self) -> bool:
        """Swap configurations between slot 1 and slot 2.

        Returns:
            True if swap was successful.

        Raises:
            CommunicationError: If command fails.
        """
        self._ensure_selected()

        try:
            _, sw1, sw2 = self._device._transport.send_apdu(
                0x00, 0x03, 0x00, 0x00
            )

            if sw1 == 0x90:
                logger.info("Slots swapped successfully")
                return True
            else:
                raise CommunicationError(f"Slot swap failed: {sw1:02X}{sw2:02X}")
        except CommunicationError:
            raise
        except Exception as e:
            raise CommunicationError(f"Slot swap error: {e}") from e

    def wipe_slot(self, slot: int, access_code: Optional[bytes] = None) -> bool:
        """Wipe/clear an OTP slot.
        
        Args:
            slot: Slot number (1 or 2).
            access_code: Required if slot is protected.
            
        Returns:
            True if wipe was successful.
            
        Raises:
            ValueError: If slot is invalid.
            CommunicationError: If command fails.
        """
        self._ensure_selected()
        
        if slot not in [1, 2]:
            raise ValueError("Slot must be 1 or 2")
        
        try:
            data = access_code if access_code else b''
            _, sw1, sw2 = self._device._transport.send_apdu(
                0x00, 0x04, slot - 1, 0x00, data=data
            )
            
            if sw1 == 0x90:
                logger.info(f"Wiped slot {slot}")
                return True
            elif sw1 == 0x69 and sw2 == 0x82:
                raise AuthenticationError("Access code required to wipe this slot")
            else:
                raise CommunicationError(f"Slot wipe failed: {sw1:02X}{sw2:02X}")
        except Exception as e:
            if not isinstance(e, (ValueError, AuthenticationError, CommunicationError)):
                raise CommunicationError(f"Slot wipe error: {e}") from e
            raise
    
    def calculate_hotp(self, secret: bytes, counter: int, digits: int = 6) -> str:
        """Calculate HOTP code locally (helper function).
        
        This is useful for verification without using the device.
        
        Args:
            secret: HMAC-SHA1 secret key.
            counter: Counter value.
            digits: Number of digits (6 or 8).
            
        Returns:
            HOTP code as string.
        """
        # RFC 4226 HOTP algorithm
        counter_bytes = struct.pack(">Q", counter)
        hmac_hash = hmac.new(secret, counter_bytes, hashlib.sha1).digest()
        
        offset = hmac_hash[-1] & 0x0F
        truncated = struct.unpack(">I", hmac_hash[offset:offset+4])[0]
        truncated &= 0x7FFFFFFF
        
        code = truncated % (10 ** digits)
        return str(code).zfill(digits)
    
    def __repr__(self) -> str:
        """Return string representation."""
        return f"OTPModule({self._device.name})"
