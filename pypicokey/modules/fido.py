"""
FIDO2/WebAuthn module for pypicokey.

This module provides FIDO2/U2F/WebAuthn functionality for interacting
with Pico FIDO devices.
"""

from typing import Optional, Any
from dataclasses import dataclass
import logging

from pypicokey.device import PicoKeyDevice
from pypicokey.constants import DeviceMode, CTAPCommand
from pypicokey.exceptions import UnsupportedModeError, CommunicationError
from pypicokey.protocol.ctap import CTAPHandler

logger = logging.getLogger(__name__)


@dataclass
class FIDOInfo:
    """FIDO2 device information."""
    
    versions: list[str]
    extensions: list[str]
    aaguid: Optional[bytes] = None
    options: dict[str, bool] = None
    max_msg_size: int = 1024
    pin_protocols: list[int] = None
    firmware_version: Optional[str] = None
    
    def __post_init__(self) -> None:
        if self.options is None:
            self.options = {}
        if self.pin_protocols is None:
            self.pin_protocols = []
    
    @property
    def supports_resident_keys(self) -> bool:
        return self.options.get("rk", False)
    
    @property
    def supports_user_presence(self) -> bool:
        return self.options.get("up", True)
    
    @property
    def supports_user_verification(self) -> bool:
        return self.options.get("uv", False)
    
    @property
    def supports_client_pin(self) -> bool:
        return self.options.get("clientPin", False)


class FIDOModule:
    """FIDO2/WebAuthn operations for Pico FIDO devices."""
    
    def __init__(self, device: PicoKeyDevice) -> None:
        """Initialize FIDO module.
        
        Args:
            device: Connected PicoKeyDevice instance.
        """
        if device.mode != DeviceMode.FIDO:
            raise UnsupportedModeError(
                "FIDO module requires a FIDO device",
                current_mode=str(device.mode),
                required_mode=str(DeviceMode.FIDO),
            )
        
        self._device = device
        self._handler = CTAPHandler(device)
        self._initialized = False

    def _ensure_init(self) -> None:
        if not self._initialized:
            if not self._handler.init_device():
                raise CommunicationError("Failed to initialize CTAPHID")
            self._initialized = True

    def get_info(self) -> FIDOInfo:
        """Get FIDO2 authenticator information using CTAP2 authenticatorGetInfo."""
        self._ensure_init()
        
        try:
            # Send getInfo (0x04)
            response = self._handler.send_cbor(CTAPCommand.AUTHENTICATOR_GET_INFO)
            
            # Use fido2 library if available for CBOR decoding
            try:
                from fido2 import cbor
                data = cbor.decode(response)
                
                return FIDOInfo(
                    versions=data.get(1, []),
                    extensions=data.get(2, []),
                    aaguid=data.get(3),
                    options=data.get(4, {}),
                    max_msg_size=data.get(5, 1024),
                    pin_protocols=data.get(6, []),
                    firmware_version=str(data.get(9)) if 9 in data else None
                )
            except ImportError:
                logger.warning("fido2 library not found, returning raw response in extra")
                return FIDOInfo(
                    versions=["unknown"],
                    extensions=[],
                    firmware_version="Lib fido2 missing"
                )
                
        except Exception as e:
            raise CommunicationError(f"Failed to get FIDO info: {e}") from e
    
    def reset(self) -> bool:
        """Reset the FIDO2 authenticator. Requires user presence."""
        self._ensure_init()
        try:
            # Send reset (0x07)
            self._handler.send_cbor(CTAPCommand.AUTHENTICATOR_RESET)
            return True
        except Exception as e:
            raise CommunicationError(f"FIDO reset failed: {e}") from e
    
    def get_retries(self) -> int:
        """Get PIN retries remaining."""
        self._ensure_init()
        try:
            from fido2 import cbor
            # authenticatorClientPIN (0x06), sub-command getRetries (0x01)
            payload = cbor.encode({1: 1}) # pinProtocol 1, subCommand getRetries
            response = self._handler.send_cbor(CTAPCommand.AUTHENTICATOR_CLIENT_PIN, payload)
            data = cbor.decode(response)
            return data.get(3) # retries
        except ImportError:
            raise UnsupportedModeError("fido2 library required for PIN operations")
        except Exception as e:
            raise CommunicationError(f"Failed to get PIN retries: {e}") from e

    def __repr__(self) -> str:
        return f"FIDOModule({self._device.name})"
