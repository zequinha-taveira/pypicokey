"""
Device provisioning for pypicokey.

This module provides device initialization and provisioning
functionality for PicoKey devices.
"""

from typing import Optional, Any
from dataclasses import dataclass, field
import logging

from pypicokey.device import PicoKeyDevice
from pypicokey.constants import DeviceMode
from pypicokey.exceptions import ProvisioningError, CommunicationError

logger = logging.getLogger(__name__)


@dataclass
class ProvisioningConfig:
    """Configuration for device provisioning."""

    device_label: str = "PicoKey"
    user_pin: str = field(default="123456", repr=False)
    admin_pin: str = field(default="12345678", repr=False)
    current_user_pin: str | None = field(default=None, repr=False)
    current_admin_pin: str | None = field(default=None, repr=False)
    reset_existing: bool = False
    generate_keys: bool = False
    key_algorithms: Optional[dict[str, str]] = None

    def __post_init__(self) -> None:
        if self.key_algorithms is None:
            self.key_algorithms = {}

    def validate(self) -> list[str]:
        errors = []
        if len(self.user_pin) < 4:
            errors.append("User PIN must be at least 4 characters")
        if len(self.admin_pin) < 8:
            errors.append("Admin PIN must be at least 8 characters")
        return errors


@dataclass
class ProvisioningResult:
    """Result of device provisioning."""
    
    success: bool
    device_mode: Optional[DeviceMode] = None
    serial_number: Optional[str] = None
    generated_keys: Optional[list[str]] = None
    errors: Optional[list[str]] = None
    
    def __post_init__(self) -> None:
        if self.generated_keys is None:
            self.generated_keys = []
        if self.errors is None:
            self.errors = []


class DeviceProvisioner:
    """Device provisioning operations."""
    
    def __init__(self, device: PicoKeyDevice) -> None:
        """Initialize the provisioner.
        
        Args:
            device: Connected PicoKeyDevice instance.
        """
        self._device = device
    
    def provision(self, config: ProvisioningConfig) -> ProvisioningResult:
        """Provision the device with the given configuration."""
        errors = config.validate()
        if errors:
            return ProvisioningResult(success=False, errors=errors)
        
        try:
            if config.reset_existing:
                self._perform_reset()
                
            if self._device.mode == DeviceMode.FIDO:
                return self._provision_fido(config)
            elif self._device.mode == DeviceMode.OPENPGP:
                return self._provision_openpgp(config)
            elif self._device.mode == DeviceMode.HSM:
                return self._provision_hsm(config)
            else:
                return ProvisioningResult(success=False, errors=[f"Provisioning not supported for mode: {self._device.mode}"])
                
        except Exception as e:
            logger.error(f"Provisioning failed: {e}")
            return ProvisioningResult(success=False, errors=[str(e)])

    def _perform_reset(self) -> None:
        """Reset the device before provisioning.
        
        Destructive steps are guarded: if the device does not support the
        reset operation, an error is raised before any destructive action
        can leave the device in a wiped state mid-provisioning.
        
        Raises:
            ProvisioningError: If reset is not supported or fails.
        """
        try:
            if self._device.mode == DeviceMode.FIDO:
                from pypicokey.modules.fido import FIDOModule
                mod = FIDOModule(self._device)
                info = mod.get_info()
                if not info.options.get("resetAllowed", True):
                    raise CommunicationError(
                        "FIDO device does not allow reset in current state"
                    )
                mod.reset()
            elif self._device.mode == DeviceMode.OPENPGP:
                from pypicokey.modules.openpgp import OpenPGPModule
                mod = OpenPGPModule(self._device)
                mod.select()
                mod.factory_reset()
            elif self._device.mode == DeviceMode.HSM:
                from pypicokey.modules.hsm import HSMModule
                mod = HSMModule(self._device)
                mod.select()
                # Verify we can talk to the applet before wiping it
                mod.get_info()
                mod.factory_reset()
            else:
                raise CommunicationError(
                    f"Reset not supported for mode: {self._device.mode}"
                )
        except Exception as e:
            raise ProvisioningError(
                f"Device reset failed, aborting provisioning: {e}",
                stage="reset",
            ) from e

    def _provision_fido(self, config: ProvisioningConfig) -> ProvisioningResult:
        from pypicokey.modules.fido import FIDOModule
        mod = FIDOModule(self._device)
        mod.set_pin(config.user_pin)
        return ProvisioningResult(success=True, device_mode=DeviceMode.FIDO)

    def _provision_openpgp(self, config: ProvisioningConfig) -> ProvisioningResult:
        from pypicokey.modules.openpgp import OpenPGPModule
        mod = OpenPGPModule(self._device)
        mod.select()

        # After a reset the card is back to factory PINs; otherwise the
        # current PINs must be supplied to be able to change them.
        if config.reset_existing:
            old_user, old_admin = "123456", "12345678"
        elif config.current_user_pin and config.current_admin_pin:
            old_user, old_admin = config.current_user_pin, config.current_admin_pin
        else:
            raise ProvisioningError(
                "OpenPGP provisioning requires either reset_existing=True or "
                "the current user/admin PINs (current_user_pin/current_admin_pin)"
            )

        mod.change_pin(old_user, config.user_pin)
        mod.change_pin(old_admin, config.admin_pin, admin=True)

        gen_keys = []
        if config.generate_keys:
            gen_keys.append("signature")
            mod.generate_key("signature")

        return ProvisioningResult(success=True, device_mode=DeviceMode.OPENPGP, generated_keys=gen_keys)

    def _provision_hsm(self, config: ProvisioningConfig) -> ProvisioningResult:
        from pypicokey.modules.hsm import HSMModule
        mod = HSMModule(self._device)
        mod.select()
        mod.initialize(config.admin_pin, config.user_pin, config.device_label)
        return ProvisioningResult(success=True, device_mode=DeviceMode.HSM)
    
    def check_state(self) -> dict[str, Any]:
        """Check the current device state for provisioning.
        
        Returns:
            Dictionary with device state information.
        """
        # TODO: Implement state checking
        logger.warning("DeviceProvisioner.check_state() is not yet implemented")
        
        return {
            "mode": str(self._device.mode),
            "initialized": False,
            "locked": False,
            "can_provision": True,
        }
    
    def __repr__(self) -> str:
        """Return string representation."""
        return f"DeviceProvisioner({self._device.name})"
