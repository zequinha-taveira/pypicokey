"""
Secure lock functionality for pypicokey.

This module provides secure lock features for protecting
PicoKey device configurations.
"""

from typing import Optional
from dataclasses import dataclass
import logging

from pypicokey.device import PicoKeyDevice
from pypicokey.exceptions import CommunicationError

logger = logging.getLogger(__name__)


@dataclass
class LockStatus:
    """Device lock status."""
    
    is_locked: bool = False
    lock_type: Optional[str] = None
    can_unlock: bool = True
    attempts_remaining: Optional[int] = None


class SecureLock:
    """Secure lock operations for PicoKey devices."""
    
    def __init__(self, device: PicoKeyDevice) -> None:
        """Initialize secure lock handler.
        
        Args:
            device: Connected PicoKeyDevice instance.
        """
        self._device = device
    
    def get_status(self) -> LockStatus:
        """Get the current lock status.

        Fails closed: communication errors raise instead of reporting an
        unlocked device.

        Raises:
            CommunicationError: If the lock status cannot be determined.
        """
        try:
            from pypicokey.constants import DeviceMode

            # Fail closed: only OpenPGP lock state can be determined today
            if self._device.mode == DeviceMode.OPENPGP:
                from pypicokey.modules.openpgp import OpenPGPModule
                mod = OpenPGPModule(self._device)
                info = mod.get_info()
                # If admin PIN retries is 0, it's effectively locked
                return LockStatus(
                    is_locked=info.admin_pin_retries == 0,
                    lock_type="smartcard_pin",
                    attempts_remaining=info.admin_pin_retries
                )

            return LockStatus(is_locked=True, can_unlock=False, lock_type="unknown")

        except CommunicationError:
            raise
        except Exception as e:
            logger.error(f"Failed to get lock status: {e}")
            raise CommunicationError(f"Could not determine lock status: {e}") from e

    def lock(self, admin_pin: str, lock_type: str = "standard") -> bool:
        """Lock the device configuration.

        Raises:
            NotImplementedError: Locking is not yet implemented.
        """
        raise NotImplementedError("SecureLock.lock not yet implemented")

    def unlock(self, admin_pin: str) -> bool:
        """Unlock the device configuration."""
        # Verify admin PIN
        try:
            from pypicokey.constants import DeviceMode
            if self._device.mode == DeviceMode.OPENPGP:
                from pypicokey.modules.openpgp import OpenPGPModule
                mod = OpenPGPModule(self._device)
                return mod.verify_pin(admin_pin, admin=True)
            return False
        except Exception:
            return False
    
    def verify_integrity(self) -> bool:
        """Verify the integrity of the locked configuration.
        
        Checks that the device configuration has not been tampered with.
        
        Returns:
            True if integrity check passes.
        """
        logger.warning("SecureLock.verify_integrity() is not yet implemented")
        raise NotImplementedError("SecureLock.verify_integrity not yet implemented")
    
    def __repr__(self) -> str:
        """Return string representation."""
        return f"SecureLock({self._device.name})"
