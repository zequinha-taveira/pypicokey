"""
FIDO2/WebAuthn module for pypicokey.

This module provides FIDO2/U2F/WebAuthn functionality for interacting
with Pico FIDO devices.
"""

from typing import Optional
from dataclasses import dataclass
import logging

from pypicokey.device import PicoKeyDevice
from pypicokey.constants import DeviceMode, CTAPCommand
from pypicokey.exceptions import (
    DeviceConnectionError,
    UnsupportedModeError,
    CommunicationError,
    AuthenticationError,
)
from pypicokey.protocol.ctap import CTAPHandler

logger = logging.getLogger(__name__)

# CTAP2 clientPin sub-commands
PIN_SUBCMD_GET_RETRIES = 0x01
PIN_SUBCMD_GET_KEY_AGREEMENT = 0x02
PIN_SUBCMD_SET_PIN = 0x03


@dataclass
class FIDOInfo:
    """FIDO2 device information."""
    
    versions: list[str]
    extensions: list[str]
    aaguid: Optional[bytes] = None
    options: Optional[dict[str, bool]] = None
    max_msg_size: int = 1024
    pin_protocols: Optional[list[int]] = None
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
        
        if device._transport is None:
            raise DeviceConnectionError(
                "Device must be connected before using the FIDO module",
                device_path=device.info.path,
            )
        
        self._device = device
        # CTAPHandler needs an object with send()/receive(): use the transport
        self._handler = CTAPHandler(device._transport)
        self._initialized = False

    def _ensure_init(self) -> None:
        if not self._initialized:
            if not self._handler.init_device():
                raise CommunicationError("Failed to initialize CTAPHID")
            self._initialized = True

    @staticmethod
    def _check_status(response: bytes, context: str) -> bytes:
        """Validate CTAP2 response and strip leading status byte.
        
        Args:
            response: Raw CTAP2 response (status byte + CBOR payload).
            context: Description of the operation for error messages.
            
        Returns:
            CBOR payload without the status byte.
        """
        if not response:
            raise CommunicationError(f"Empty response for {context}")
        if response[0] != 0x00:
            raise CommunicationError(
                f"{context} failed with status 0x{response[0]:02X}",
                response_code=response[0],
            )
        return response[1:]

    def get_info(self) -> FIDOInfo:
        """Get FIDO2 authenticator information using CTAP2 authenticatorGetInfo."""
        self._ensure_init()
        
        try:
            # Send getInfo (0x04)
            response = self._handler.send_cbor(CTAPCommand.AUTHENTICATOR_GET_INFO)
            
            # Use fido2 library if available for CBOR decoding
            try:
                from fido2 import cbor
                data = cbor.decode(self._check_status(response, "authenticatorGetInfo"))
                
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
                
        except CommunicationError:
            raise
        except Exception as e:
            raise CommunicationError(f"Failed to get FIDO info: {e}") from e
    
    def reset(self) -> bool:
        """Reset the FIDO2 authenticator. Requires user presence."""
        self._ensure_init()
        try:
            # Send reset (0x07)
            response = self._handler.send_cbor(CTAPCommand.AUTHENTICATOR_RESET)
            self._check_status(response, "authenticatorReset")
            return True
        except CommunicationError:
            raise
        except Exception as e:
            raise CommunicationError(f"FIDO reset failed: {e}") from e

    def _client_pin(self, request: dict) -> dict:
        """Send an authenticatorClientPIN request and decode the response."""
        from fido2 import cbor
        payload = cbor.encode(request)
        response = self._handler.send_cbor(CTAPCommand.AUTHENTICATOR_CLIENT_PIN, payload)
        data = cbor.decode(self._check_status(response, "authenticatorClientPIN"))
        return data or {}
    
    def get_retries(self) -> int:
        """Get PIN retries remaining."""
        self._ensure_init()
        try:
            # authenticatorClientPIN (0x06), sub-command getRetries (0x01)
            data = self._client_pin({1: 1, 2: PIN_SUBCMD_GET_RETRIES})
            return data.get(3) # retries
        except ImportError as e:
            raise UnsupportedModeError(
                "fido2 library required for PIN operations"
            ) from e
        except CommunicationError:
            raise
        except Exception as e:
            raise CommunicationError(f"Failed to get PIN retries: {e}") from e
    
    def set_pin(self, pin: str) -> bool:
        """Set the PIN using the CTAP2 clientPin setPin protocol.
        
        Implements the PIN/UV auth protocol 1 flow:
        1. Get the authenticator's ephemeral ECDH P-256 public key (getKeyAgreement).
        2. Derive a shared secret via ECDH.
        3. Encrypt the padded PIN with AES-256-CBC (zero IV).
        4. Authenticate the encrypted PIN with truncated HMAC-SHA256.
        
        Args:
            pin: New PIN (4-63 bytes after UTF-8 encoding).
            
        Returns:
            True if the PIN was set.
            
        Raises:
            ValueError: If the PIN length is invalid.
            UnsupportedModeError: If required crypto libraries are missing.
            CommunicationError: If the device rejects the operation.
        """
        self._ensure_init()
        
        try:
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives import hashes, hmac
        except ImportError as e:
            raise UnsupportedModeError(
                "cryptography library required for PIN operations"
            ) from e
        
        pin_bytes = pin.encode("utf-8")
        if not 4 <= len(pin_bytes) < 64:
            raise ValueError("PIN must be between 4 and 63 characters")
        
        try:
            # 1. Authenticator's ephemeral public key (COSE key format)
            cose_key = self._client_pin(
                {1: 1, 2: PIN_SUBCMD_GET_KEY_AGREEMENT}
            ).get(1)
            if cose_key is None:
                raise CommunicationError("Device did not provide key agreement key")
            
            peer_pub = ec.EllipticCurvePublicKey.from_encoded_point(
                ec.SECP256R1(),
                b"\x04" + cose_key[-2] + cose_key[-3],
            )
            
            # 2. Shared secret = x coordinate of our ephemeral ECDH point
            our_priv = ec.generate_private_key(ec.SECP256R1())
            shared_secret = our_priv.exchange(ec.ECDH(), peer_pub)
            
            # 3. Encrypt zero-padded PIN with AES-256-CBC, IV all zeros
            padded = pin_bytes.ljust(64, b"\x00")
            encryptor = Cipher(
                algorithms.AES(shared_secret), modes.CBC(b"\x00" * 16)
            ).encryptor()
            new_pin_enc = encryptor.update(padded) + encryptor.finalize()
            
            # 4. Truncated HMAC-SHA256 over the encrypted PIN
            h = hmac.HMAC(shared_secret, hashes.SHA256())
            h.update(new_pin_enc)
            pin_auth = h.finalize()[:16]
            
            pub_nums = our_priv.public_key().public_numbers()
            our_cose_key = {
                1: 2,      # kty: EC2
                3: -25,    # alg: ECDH-ES+HKDF-256
                -1: 1,     # crv: P-256
                -2: pub_nums.x.to_bytes(32, "big"),
                -3: pub_nums.y.to_bytes(32, "big"),
            }
            
            self._client_pin({
                1: 1,                          # pinProtocol
                2: PIN_SUBCMD_SET_PIN,         # subCommand: setPin
                3: our_cose_key,               # keyAgreement
                4: pin_auth,                   # pinAuth
                5: new_pin_enc,                # newPinEnc
            })
            logger.info("FIDO PIN set successfully")
            return True
        except AuthenticationError:
            raise
        except CommunicationError:
            raise
        except Exception as e:
            raise CommunicationError(f"Failed to set PIN: {e}") from e

    def __repr__(self) -> str:
        return f"FIDOModule({self._device.name})"
