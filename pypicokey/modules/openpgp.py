"""
OpenPGP module for pypicokey.

This module provides OpenPGP smartcard functionality for interacting
with Pico OpenPGP devices.
"""

from typing import Optional, Any
from dataclasses import dataclass
import logging

from pypicokey.device import PicoKeyDevice
from pypicokey.constants import DeviceMode, OpenPGPInstruction
from pypicokey.exceptions import UnsupportedModeError, CommunicationError
from pypicokey.protocol.openpgp_apdu import OpenPGPAPDU, TLVParser

logger = logging.getLogger(__name__)


@dataclass
class OpenPGPInfo:
    """OpenPGP card information."""
    
    aid: Optional[bytes] = None
    version: Optional[str] = None
    manufacturer: Optional[str] = None
    serial_number: Optional[str] = None
    pin_retries: tuple[int, int, int] = (3, 0, 3)
    signature_count: int = 0
    key_slots: dict[str, dict[str, Any]] = None
    
    def __post_init__(self) -> None:
        if self.key_slots is None:
            self.key_slots = {
                "signature": {},
                "encryption": {},
                "authentication": {},
            }
    
    @property
    def user_pin_retries(self) -> int:
        return self.pin_retries[0]
    
    @property
    def admin_pin_retries(self) -> int:
        return self.pin_retries[2]


class OpenPGPModule:
    """OpenPGP operations for Pico OpenPGP devices."""
    
    # OpenPGP AID
    AID = bytes.fromhex("D27600012401")
    
    # OpenPGP Tags
    TAG_AID = 0x004F
    TAG_LOGIN = 0x005E
    TAG_HISTORICAL = 0x5F52
    TAG_PW_STATUS = 0x00C4
    
    def __init__(self, device: PicoKeyDevice) -> None:
        """Initialize OpenPGP module.
        
        Args:
            device: Connected PicoKeyDevice instance.
        """
        if device.mode != DeviceMode.OPENPGP:
            raise UnsupportedModeError(
                "OpenPGP module requires an OpenPGP device",
                current_mode=str(device.mode),
                required_mode=str(DeviceMode.OPENPGP),
            )
        
        self._device = device
        self._selected = False

    def _ensure_selected(self) -> None:
        if not self._selected:
            self.select()

    def select(self) -> bool:
        """Select the OpenPGP application."""
        try:
            # The device.connect() should have been called outside
            # We use the raw transport from the device
            from pypicokey.transport.ccid import CCIDTransport
            if not isinstance(self._device._transport, CCIDTransport):
                raise CommunicationError("Device transport is not CCID")
                
            response, sw1, sw2 = self._device._transport.select_application(self.AID)
            if sw1 == 0x90 and sw2 == 0x00:
                self._selected = True
                return True
            else:
                raise CommunicationError(f"Failed to select OpenPGP application: {sw1:02X}{sw2:02X}")
        except Exception as e:
            raise CommunicationError(f"OpenPGP selection failed: {e}") from e
    
    def get_info(self) -> OpenPGPInfo:
        """Get OpenPGP card information via GET DATA commands."""
        self._ensure_selected()
        
        try:
            # 1. Get PW Status (retries)
            resp, sw1, sw2 = self._device._transport.send_apdu(0x00, 0xCA, 0x00, 0xC4, le=0)
            pin_retries = (3, 0, 3)
            if sw1 == 0x90 and len(resp) >= 7:
                pin_retries = (resp[4], resp[5], resp[6])
                
            # 2. Get AID/Serial
            resp, sw1, sw2 = self._device._transport.send_apdu(0x00, 0xCA, 0x00, 0x4F, le=0)
            serial = resp.hex() if sw1 == 0x90 else None
            
            # 3. Get Application Related Data (0x6E)
            # This is a large TLV block with lots of info
            resp, sw1, sw2 = self._device._transport.send_apdu(0x00, 0xCA, 0x00, 0x6E, le=0)
            version = "unknown"
            if sw1 == 0x90:
                # Parse TLV to find version and other fields
                tags = TLVParser.parse(resp)
                # Historical bytes might have version
                hist = tags.get(0x5F52, b"")
                if len(hist) >= 4:
                    version = f"{hist[2]}.{hist[3]}"

            return OpenPGPInfo(
                aid=self.AID,
                version=version,
                serial_number=serial,
                pin_retries=pin_retries,
                manufacturer="PicoKeys"
            )
            
        except Exception as e:
            raise CommunicationError(f"Failed to get OpenPGP info: {e}") from e
    
    def verify_pin(self, pin: str, admin: bool = False) -> bool:
        """Verify user or admin PIN."""
        self._ensure_selected()
        try:
            p2 = 0x83 if admin else 0x81
            pin_bytes = pin.encode("utf-8")
            _, sw1, sw2 = self._device._transport.send_apdu(0x00, 0x20, 0x00, p2, data=pin_bytes)
            
            if sw1 == 0x90:
                return True
            elif sw1 == 0x63:
                retries = sw2 & 0x0F
                from pypicokey.exceptions import AuthenticationError
                raise AuthenticationError("Incorrect PIN", retries_remaining=retries)
            else:
                raise CommunicationError(f"PIN verification failed: {sw1:02X}{sw2:02X}")
        except Exception as e:
            if not isinstance(e, (CommunicationError, AuthenticationError)):
                raise CommunicationError(f"PIN verification error: {e}") from e
            raise

    def __repr__(self) -> str:
        return f"OpenPGPModule({self._device.name})"
    
    def change_pin(self, old_pin: str, new_pin: str, admin: bool = False) -> bool:
        """Change user or admin PIN.
        
        Args:
            old_pin: Current PIN.
            new_pin: New PIN.
            admin: If True, change admin PIN; otherwise user PIN.
            
        Returns:
            True if PIN was changed.
            
        Raises:
            CommunicationError: If command fails.
        """
        # TODO: Implement CHANGE REFERENCE DATA command
        logger.warning("OpenPGPModule.change_pin() is not yet implemented")
        raise NotImplementedError("OpenPGP change_pin not yet implemented")
    
    def reset_retry_counter(self, admin_pin: str, new_user_pin: str) -> bool:
        """Reset user PIN retry counter and set new PIN.
        
        Requires admin PIN.
        
        Args:
            admin_pin: Admin PIN for authentication.
            new_user_pin: New user PIN to set.
            
        Returns:
            True if reset was successful.
            
        Raises:
            CommunicationError: If command fails.
        """
        # TODO: Implement RESET RETRY COUNTER command
        logger.warning("OpenPGPModule.reset_retry_counter() is not yet implemented")
        raise NotImplementedError("OpenPGP reset_retry_counter not yet implemented")
    
    def get_public_key(self, slot: str) -> Optional[bytes]:
        """Get public key from a slot.
        
        Args:
            slot: Key slot ("signature", "encryption", or "authentication").
            
        Returns:
            Public key bytes, or None if slot is empty.
            
        Raises:
            CommunicationError: If command fails.
        """
        # TODO: Implement GET PUBLIC KEY command
        logger.warning("OpenPGPModule.get_public_key() is not yet implemented")
        raise NotImplementedError("OpenPGP get_public_key not yet implemented")
    
    def generate_key(self, slot: str, algorithm: str = "rsa2048") -> bytes:
        """Generate a new key pair in a slot.
        
        Args:
            slot: Key slot ("signature", "encryption", or "authentication").
            algorithm: Key algorithm (e.g., "rsa2048", "cv25519").
            
        Returns:
            Public key bytes.
            
        Raises:
            CommunicationError: If command fails.
        """
        # TODO: Implement GENERATE ASYMMETRIC KEY PAIR command
        logger.warning("OpenPGPModule.generate_key() is not yet implemented")
        raise NotImplementedError("OpenPGP generate_key not yet implemented")
    
    def factory_reset(self) -> bool:
        """Perform factory reset of the OpenPGP card.
        
        WARNING: This will delete all keys and reset PINs to defaults.
        
        Returns:
            True if reset was successful.
            
        Raises:
            CommunicationError: If command fails.
        """
        # TODO: Implement factory reset sequence
        logger.warning("OpenPGPModule.factory_reset() is not yet implemented")
        raise NotImplementedError("OpenPGP factory_reset not yet implemented")
    
    def __repr__(self) -> str:
        """Return string representation."""
        return f"OpenPGPModule({self._device.name})"
