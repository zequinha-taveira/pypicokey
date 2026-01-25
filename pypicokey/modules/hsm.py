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
    
    state: HSMState = HSMState.UNINITIALIZED
    version: Optional[str] = None
    serial_number: Optional[str] = None
    total_slots: int = 0
    used_slots: int = 0
    pin_retries: int = 3
    so_pin_retries: int = 3
    
    @property
    def is_initialized(self) -> bool:
        return self.state != HSMState.UNINITIALIZED
    
    @property
    def is_locked(self) -> bool:
        return self.state == HSMState.LOCKED
    
    @property
    def available_slots(self) -> int:
        return self.total_slots - self.used_slots


class HSMModule:
    """HSM operations for Pico HSM devices."""
    
    # HSM AID
    AID = bytes.fromhex("E828BD080F014E58534D1001") # Example SmartCard-HSM AID
    
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
            # Get Info APDU (example: 00 CA 01 01)
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

    def __repr__(self) -> str:
        return f"HSMModule({self._device.name})"
    
    def logout(self) -> bool:
        """Logout from the HSM.
        
        Returns:
            True if logout was successful.
        """
        # TODO: Implement HSM logout
        logger.warning("HSMModule.logout() is not yet implemented")
        raise NotImplementedError("HSM logout not yet implemented")
    
    def list_keys(self) -> list[KeyInfo]:
        """List all keys in the HSM.
        
        Returns:
            List of KeyInfo objects.
            
        Raises:
            CommunicationError: If command fails.
        """
        # TODO: Implement key listing
        logger.warning("HSMModule.list_keys() is not yet implemented")
        raise NotImplementedError("HSM list_keys not yet implemented")
    
    def generate_key(
        self,
        label: str,
        key_type: str = "RSA",
        key_size: int = 2048,
        extractable: bool = False,
    ) -> KeyInfo:
        """Generate a new key in the HSM.
        
        Args:
            label: Key label.
            key_type: Key type ("RSA", "EC", "AES").
            key_size: Key size in bits.
            extractable: Whether key can be exported.
            
        Returns:
            KeyInfo for the generated key.
            
        Raises:
            CommunicationError: If command fails.
        """
        # TODO: Implement key generation
        logger.warning("HSMModule.generate_key() is not yet implemented")
        raise NotImplementedError("HSM generate_key not yet implemented")
    
    def delete_key(self, slot: int) -> bool:
        """Delete a key from the HSM.
        
        Args:
            slot: Key slot to delete.
            
        Returns:
            True if key was deleted.
            
        Raises:
            CommunicationError: If command fails.
        """
        # TODO: Implement key deletion
        logger.warning("HSMModule.delete_key() is not yet implemented")
        raise NotImplementedError("HSM delete_key not yet implemented")
    
    def sign(self, slot: int, data: bytes, mechanism: str = "RSA-PKCS") -> bytes:
        """Sign data using a key in the HSM.
        
        Args:
            slot: Key slot to use.
            data: Data to sign.
            mechanism: Signing mechanism.
            
        Returns:
            Signature bytes.
            
        Raises:
            CommunicationError: If command fails.
        """
        # TODO: Implement signing
        logger.warning("HSMModule.sign() is not yet implemented")
        raise NotImplementedError("HSM sign not yet implemented")
    
    def factory_reset(self) -> bool:
        """Perform factory reset of the HSM.
        
        WARNING: This will delete all keys and reset to uninitialized state.
        
        Returns:
            True if reset was successful.
            
        Raises:
            CommunicationError: If command fails.
        """
        # TODO: Implement factory reset
        logger.warning("HSMModule.factory_reset() is not yet implemented")
        raise NotImplementedError("HSM factory_reset not yet implemented")
    
    def __repr__(self) -> str:
        """Return string representation."""
        return f"HSMModule({self._device.name})"
