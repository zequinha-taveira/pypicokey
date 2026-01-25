"""
Device provisioning for pypicokey.

This module provides device initialization and provisioning
functionality for PicoKey devices.
"""

from pypicokey.device import PicoKeyDevice
from pypicokey.constants import DeviceMode
from pypicokey.exceptions import ProvisioningError, CommunicationError

logger = logging.getLogger(__name__)


@dataclass
class ProvisioningConfig:
    """Configuration for device provisioning."""
    
    device_label: str = "PicoKey"
    user_pin: str = "123456"
    admin_pin: str = "12345678"
    reset_existing: bool = False
    generate_keys: bool = False
    key_algorithms: dict[str, str] = None
    
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
    generated_keys: list[str] = None
    errors: list[str] = None
    
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
        if self._device.mode == DeviceMode.FIDO:
            from pypicokey.modules.fido import FIDOModule
            mod = FIDOModule(self._device)
            mod.reset()
        elif self._device.mode == DeviceMode.OPENPGP:
            from pypicokey.modules.openpgp import OpenPGPModule
            mod = OpenPGPModule(self._device)
            mod.factory_reset()
        elif self._device.mode == DeviceMode.HSM:
            from pypicokey.modules.hsm import HSMModule
            mod = HSMModule(self._device)
            mod.factory_reset()

    def _provision_fido(self, config: ProvisioningConfig) -> ProvisioningResult:
        from pypicokey.modules.fido import FIDOModule
        mod = FIDOModule(self._device)
        mod.set_pin(config.user_pin)
        return ProvisioningResult(success=True, device_mode=DeviceMode.FIDO)

    def _provision_openpgp(self, config: ProvisioningConfig) -> ProvisioningResult:
        from pypicokey.modules.openpgp import OpenPGPModule
        mod = OpenPGPModule(self._device)
        mod.select()
        # Change default PINs
        # 123456 (PW1), 12345678 (PW3)
        mod.change_pin("123456", config.user_pin)
        mod.change_pin("12345678", config.admin_pin, admin=True)
        
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
