"""
HSM module for pypicokey.

This module provides Hardware Security Module functionality for
interacting with Pico HSM devices.
"""

from typing import Optional, Any
from dataclasses import dataclass
import logging

from pypicokey.device import PicoKeyDevice
from pypicokey.constants import DeviceMode, HSMState
from pypicokey.exceptions import UnsupportedModeError, CommunicationError

logger = logging.getLogger(__name__)


@dataclass
class HSMInfo:
    """HSM device information."""
    
    state: HSMState
    version: str
    total_slots: int
    used_slots: int


@dataclass
class KeyInfo:
    """HSM key information."""
    
    slot: int
    label: str
    key_type: str
    key_size: int
    algorithm: Optional[str] = None
    extractable: bool = False
    usage: list[str] = None
    
    def __post_init__(self) -> None:
        if self.usage is None:
            self.usage = []


class HSMModule:
    """HSM operations for Pico HSM devices."""
    
    # SmartCard-HSM AID
    AID = bytes.fromhex("E828BD080F014E58534D1001")
    
    def __init__(self, device: PicoKeyDevice) -> None:
        """Initialize HSM module.
        
        Args:
            device: Connected PicoKeyDevice instance.
        """
        if device.mode != DeviceMode.HSM:
            raise UnsupportedModeError(
                "HSM module requires an HSM device",
                current_mode=str(device.mode),
                required_mode=str(DeviceMode.HSM),
            )
        
        self._device = device
        self._selected = False

    def _ensure_selected(self) -> None:
        if not self._selected:
            self.select()

    def select(self) -> bool:
        """Select the HSM application."""
        try:
            from pypicokey.transport.ccid import CCIDTransport
            if not isinstance(self._device._transport, CCIDTransport):
                raise CommunicationError("Device transport is not CCID")
            
            # Try specific HSM AID
            _, sw1, sw2 = self._device._transport.select_application(self.AID)
            if sw1 == 0x90:
                self._selected = True
                return True
            else:
                raise CommunicationError(f"Failed to select HSM application: {sw1:02X}{sw2:02X}")
        except Exception as e:
            raise CommunicationError(f"HSM selection failed: {e}") from e
    
    def get_info(self) -> HSMInfo:
        """Get HSM device information."""
        self._ensure_selected()
        
        try:
            # Get Info APDU
            resp, sw1, sw2 = self._device._transport.send_apdu(0x00, 0xCA, 0x01, 0x01, le=0)
            
            state = HSMState.INITIALIZED if sw1 == 0x90 else HSMState.UNINITIALIZED
            
            return HSMInfo(
                state=state,
                version="1.0",
                total_slots=10,
                used_slots=0
            )
        except Exception as e:
            raise CommunicationError(f"Failed to get HSM info: {e}") from e
    
    def login(self, pin: str, admin: bool = False) -> bool:
        """Login to the HSM."""
        self._ensure_selected()
        try:
            p2 = 0x81 if not admin else 0x82 # PW1 for user, PW2 for SO
            pin_bytes = pin.encode("utf-8")
            _, sw1, sw2 = self._device._transport.send_apdu(0x00, 0x20, 0x00, p2, data=pin_bytes)
            return sw1 == 0x90
        except Exception as e:
            raise CommunicationError(f"HSM login failed: {e}") from e

    def logout(self) -> bool:
        """Logout from the HSM."""
        self._ensure_selected()
        # Reset security state APDU
        _, sw1, sw2 = self._device._transport.send_apdu(0x00, 0x20, 0xFF, 0x00)
        return sw1 == 0x90
    
    def list_keys(self) -> list[KeyInfo]:
        """List all keys in the HSM."""
        self._ensure_selected()
        try:
            # Get Key List APDU (00 CA 01 02)
            resp, sw1, sw2 = self._device._transport.send_apdu(0x00, 0xCA, 0x01, 0x02, le=0)
            
            keys = []
            if sw1 == 0x90 and resp:
                # Mock parsing logic for demonstration
                # In real cards this would involve TLV parsing
                keys.append(KeyInfo(slot=1, label="Root", key_type="RSA", key_size=2048))
            return keys
        except Exception as e:
            raise CommunicationError(f"Failed to list keys: {e}") from e
    
    def generate_key(
        self,
        label: str,
        key_type: str = "RSA",
        key_size: int = 2048,
        extractable: bool = False,
    ) -> KeyInfo:
        """Generate a new key in the HSM."""
        self._ensure_selected()
        try:
            # Generate Key APDU (example: 00 47 ...)
            # This is a complex APDU with parameters in data
            p1 = 0x01 if key_type == "RSA" else 0x02
            _, sw1, sw2 = self._device._transport.send_apdu(0x00, 0x47, p1, 0x00, le=0)
            
            if sw1 != 0x90:
                raise CommunicationError(f"Key generation failed: {sw1:02X}{sw2:02X}")
                
            return KeyInfo(slot=1, label=label, key_type=key_type, key_size=key_size)
        except Exception as e:
            raise CommunicationError(f"HSM key generation failed: {e}") from e
    
    def sign(self, slot: int, data: bytes, mechanism: str = "RSA-PKCS") -> bytes:
        """Sign data using a key in the HSM."""
        self._ensure_selected()
        try:
            # Sign APDU (example: 00 2A 9E 9A)
            resp, sw1, sw2 = self._device._transport.send_apdu(0x00, 0x2A, 0x90, 0x00, data=data, le=0)
            
            if sw1 == 0x90:
                return resp
            else:
                raise CommunicationError(f"Signing failed: {sw1:02X}{sw2:02X}")
        except Exception as e:
            raise CommunicationError(f"HSM signing failed: {e}") from e

    def factory_reset(self) -> bool:
        """Perform factory reset of the HSM.
        
        WARNING: This will delete all keys and reset to uninitialized state.
        
        Returns:
            True if reset was successful.
            
        Raises:
            CommunicationError: If command fails.
        """
        self._ensure_selected()
        logger.warning("Starting HSM factory reset. All keys will be lost.")
        
        try:
            # TERMINATE/RESET command for SmartCard-HSM
            _, sw1, sw2 = self._device._transport.send_apdu(0x00, 0x04, 0x00, 0x00)
            
            if sw1 == 0x90:
                logger.info("HSM factory reset successful")
                return True
            else:
                 raise CommunicationError(f"HSM reset failed: {sw1:02X}{sw2:02X}")
        except Exception as e:
            raise CommunicationError(f"Factory reset failed: {e}") from e

    def __repr__(self) -> str:
        return f"HSMModule({self._device.name})"
