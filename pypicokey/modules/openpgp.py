"""
OpenPGP module for pypicokey.

This module provides OpenPGP smartcard functionality for interacting
with Pico OpenPGP devices.
"""

from typing import Any, Optional
from dataclasses import dataclass
import logging

from pypicokey.device import PicoKeyDevice
from pypicokey.constants import DeviceMode
from pypicokey.exceptions import UnsupportedModeError, CommunicationError
from pypicokey.protocol.openpgp_apdu import TLVParser

logger = logging.getLogger(__name__)

# Shared key reference bytes for OpenPGP key slots (used by GET/GENERATE key)
SLOT_KEY_REFS = {
    "signature": 0xB6,
    "encryption": 0xB8,
    "authentication": 0xA4,
}


@dataclass
class OpenPGPInfo:
    """OpenPGP card information."""
    
    aid: Optional[bytes] = None
    version: Optional[str] = None
    manufacturer: Optional[str] = None
    serial_number: Optional[str] = None
    pin_retries: tuple[int, int, int] = (3, 0, 3)
    signature_count: int = 0
    key_slots: Optional[dict[str, dict[str, Any]]] = None
    
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
        except CommunicationError:
            raise
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
        self._ensure_selected()
        try:
            p2 = 0x83 if admin else 0x81
            old_bytes = old_pin.encode("utf-8")
            new_bytes = new_pin.encode("utf-8")
            data = old_bytes + new_bytes
            
            # CHANGE REFERENCE DATA (0x24)
            _, sw1, sw2 = self._device._transport.send_apdu(0x00, 0x24, 0x00, p2, data=data)
            
            if sw1 == 0x90:
                logger.info(f"{'Admin' if admin else 'User'} PIN changed successfully")
                return True
            elif sw1 == 0x63:
                retries = sw2 & 0x0F
                from pypicokey.exceptions import AuthenticationError
                raise AuthenticationError("Incorrect current PIN", retries_remaining=retries)
            else:
                raise CommunicationError(f"PIN change failed: {sw1:02X}{sw2:02X}")
        except Exception as e:
            if not isinstance(e, (CommunicationError, AuthenticationError)):
                raise CommunicationError(f"PIN change error: {e}") from e
            raise
    
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
        self._ensure_selected()
        
        if slot not in SLOT_KEY_REFS:
            raise ValueError(
                f"Invalid slot: {slot}. Must be one of {list(SLOT_KEY_REFS.keys())}"
            )
        
        try:
            # GET PUBLIC KEY (00 47 80 00) with tag DO for the slot
            # First, set the correct key reference
            key_ref = bytes([SLOT_KEY_REFS[slot]])
            _, sw1, sw2 = self._device._transport.send_apdu(0x00, 0xA4, 0x01, 0x00, data=key_ref)
            
            if sw1 != 0x90:
                raise CommunicationError(f"Failed to select key slot: {sw1:02X}{sw2:02X}")
            
            # Now read the public key
            resp, sw1, sw2 = self._device._transport.send_apdu(0x00, 0xCA, 0x7F, 0x49, le=0)
            
            if sw1 == 0x90 and resp:
                # Parse TLV to extract the actual public key
                tags = TLVParser.parse(resp)
                # Tag 0x86 contains the public key material
                return tags.get(0x86, resp)
            elif sw1 == 0x6A and sw2 == 0x88:
                # Key slot is empty
                return None
            else:
                raise CommunicationError(f"Failed to get public key: {sw1:02X}{sw2:02X}")
        except Exception as e:
            if not isinstance(e, (CommunicationError, ValueError)):
                raise CommunicationError(f"Get public key error: {e}") from e
            raise
    
    def generate_key(self, slot: str, algorithm: str = "rsa2048") -> bytes:
        """Generate a new key pair in a slot.
        
        Args:
            slot: Key slot ("signature", "encryption", or "authentication").
            algorithm: Key algorithm (e.g., "rsa2048", "rsa4096", "cv25519", "nistp256", "nistp384").
            
        Returns:
            Public key bytes.
            
        Raises:
            CommunicationError: If command fails.
        """
        self._ensure_selected()
        
        algo_map = {
            "rsa2048": bytes([0x01]),
            "rsa4096": bytes([0x02]),
            "cv25519": bytes([0x12]),
            "nistp256": bytes([0x13]),
            "nistp384": bytes([0x14]),
            "nistp521": bytes([0x15]),
            "brainpoolp256r1": bytes([0x16]),
            "brainpoolp384r1": bytes([0x17]),
            "brainpoolp512r1": bytes([0x18]),
        }
        
        if slot not in SLOT_KEY_REFS:
            raise ValueError(f"Invalid slot: {slot}")
        if algorithm not in algo_map:
            raise ValueError(f"Unsupported algorithm: {algorithm}. Supported: {list(algo_map.keys())}")
        
        try:
            # Set algorithm attributes first
            algo_data = algo_map[algorithm]
            attr_p2 = 0xC1 if slot == "signature" else 0xC2 if slot == "encryption" else 0xC3
            
            # PUT DATA for algorithm attributes
            _, sw1, sw2 = self._device._transport.send_apdu(
                0x00, 0xDA, 0x00, attr_p2, data=algo_data
            )
            if sw1 != 0x90:
                raise CommunicationError(f"Failed to set algorithm: {sw1:02X}{sw2:02X}")
            
            # GENERATE ASYMMETRIC KEY PAIR (00 47 80 00)
            # Data contains template with key reference
            key_ref = bytes([SLOT_KEY_REFS[slot], 0x00])
            resp, sw1, sw2 = self._device._transport.send_apdu(0x00, 0x47, 0x80, 0x00, data=key_ref, le=0)
            
            if sw1 == 0x90 and resp:
                logger.info(f"Generated {algorithm} key in {slot} slot")
                # Parse response to get public key
                tags = TLVParser.parse(resp)
                return tags.get(0x86, resp)
            else:
                raise CommunicationError(f"Key generation failed: {sw1:02X}{sw2:02X}")
        except Exception as e:
            if not isinstance(e, (CommunicationError, ValueError)):
                raise CommunicationError(f"Key generation error: {e}") from e
            raise
    
    def factory_reset(self) -> bool:
        """Perform factory reset of the OpenPGP card.
        
        WARNING: This will delete all keys and reset PINs to defaults.
        The sequence involves:
        1. Exhaust User PIN retries
        2. Exhaust Admin PIN retries
        3. TERMINATE (0x00, 0xE6, 0x00, 0x00)
        4. ACTIVATE (0x00, 0x44, 0x00, 0x00)
        
        Returns:
            True if reset was successful.
            
        Raises:
            CommunicationError: If command fails.
        """
        self._ensure_selected()
        logger.warning("Starting OpenPGP factory reset. All keys will be lost.")
        
        try:
            # 1 & 2: Exhaust PINs by sending dummy data
            dummy_pin = b"wrong"
            for p2 in [0x81, 0x83]:
                while True:
                    _, sw1, sw2 = self._device._transport.send_apdu(0x00, 0x20, 0x00, p2, data=dummy_pin)
                    if sw1 == 0x69 and (sw2 == 0x83 or sw2 == 0x84): # Locked
                        break
                    if sw1 != 0x63: # Error other than wrong PIN
                        break
            
            # 3. TERMINATE
            _, sw1, sw2 = self._device._transport.send_apdu(0x00, 0xE6, 0x00, 0x00)
            if sw1 == 0x6D and sw2 == 0x00: # Instruction not supported
                 raise CommunicationError("Device does not support TERMINATE/factory reset")
            
            # 4. ACTIVATE
            _, sw1, sw2 = self._device._transport.send_apdu(0x00, 0x44, 0x00, 0x00)
            if sw1 == 0x90:
                logger.info("OpenPGP factory reset successful")
                self._selected = False # Need to re-select
                return True
            else:
                raise CommunicationError(f"ACTIVATE failed: {sw1:02X}{sw2:02X}")
                
        except Exception as e:
            raise CommunicationError(f"Factory reset failed: {e}") from e
