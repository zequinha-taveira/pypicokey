"""
HSM module for pypicokey.

This module provides Hardware Security Module functionality for
interacting with Pico HSM devices, including support for
post-quantum cryptography algorithms (future).
"""

from typing import Optional
from dataclasses import dataclass
import logging

from pypicokey.device import PicoKeyDevice
from pypicokey.constants import DeviceMode, HSMState
from pypicokey.exceptions import (
    AuthenticationError,
    CommunicationError,
    UnsupportedModeError,
)

logger = logging.getLogger(__name__)


@dataclass
class HSMInfo:
    """HSM device information."""

    state: HSMState
    version: str | None = None
    total_slots: int | None = None
    used_slots: int | None = None


@dataclass
class KeyInfo:
    """HSM key information."""
    
    slot: int
    label: str
    key_type: str
    key_size: int
    algorithm: Optional[str] = None
    extractable: bool = False
    usage: Optional[list[str]] = None
    
    def __post_init__(self) -> None:
        if self.usage is None:
            self.usage = []


@dataclass
class PQAlgorithm:
    """Post-Quantum algorithm specification."""
    
    name: str
    family: str  # "KEM" or "Signature"
    security_level: int  # NIST level (1, 3, 5)
    public_key_size: int
    private_key_size: int
    ciphertext_or_signature_size: int
    standardized: bool  # True if NIST standardized


# Post-Quantum Algorithms Roadmap
# Based on NIST FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), FIPS 205 (SLH-DSA)
PQ_ALGORITHMS = {
    # ML-KEM (Kyber) - Key Encapsulation
    "ml-kem-512": PQAlgorithm(
        name="ML-KEM-512",
        family="KEM",
        security_level=1,
        public_key_size=800,
        private_key_size=1632,
        ciphertext_or_signature_size=768,
        standardized=True
    ),
    "ml-kem-768": PQAlgorithm(
        name="ML-KEM-768",
        family="KEM",
        security_level=3,
        public_key_size=1184,
        private_key_size=2400,
        ciphertext_or_signature_size=1088,
        standardized=True
    ),
    "ml-kem-1024": PQAlgorithm(
        name="ML-KEM-1024",
        family="KEM",
        security_level=5,
        public_key_size=1568,
        private_key_size=3168,
        ciphertext_or_signature_size=1568,
        standardized=True
    ),
    # ML-DSA (Dilithium) - Digital Signature
    "ml-dsa-44": PQAlgorithm(
        name="ML-DSA-44",
        family="Signature",
        security_level=2,
        public_key_size=1312,
        private_key_size=2400,
        ciphertext_or_signature_size=4628,
        standardized=True
    ),
    "ml-dsa-65": PQAlgorithm(
        name="ML-DSA-65",
        family="Signature",
        security_level=3,
        public_key_size=1952,
        private_key_size=4000,
        ciphertext_or_signature_size=3309,
        standardized=True
    ),
    "ml-dsa-87": PQAlgorithm(
        name="ML-DSA-87",
        family="Signature",
        security_level=5,
        public_key_size=2592,
        private_key_size=4864,
        ciphertext_or_signature_size=4595,
        standardized=True
    ),
    # SLH-DSA (Sphincs+) - Digital Signature (stateless)
    "slh-dsa-shake-128s": PQAlgorithm(
        name="SLH-DSA-SHAKE-128s",
        family="Signature",
        security_level=1,
        public_key_size=32,
        private_key_size=64,
        ciphertext_or_signature_size=7856,
        standardized=True
    ),
}


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
            )
        except Exception as e:
            raise CommunicationError(f"Failed to get HSM info: {e}") from e

    def login(self, pin: str, admin: bool = False) -> bool:
        """Login to the HSM.

        Returns:
            True on successful login.

        Raises:
            AuthenticationError: If the PIN is wrong (includes retries left).
            CommunicationError: If the command fails.
        """
        self._ensure_selected()
        try:
            p2 = 0x81 if not admin else 0x82 # PW1 for user, PW2 for SO
            pin_bytes = pin.encode("utf-8")
            _, sw1, sw2 = self._device._transport.send_apdu(0x00, 0x20, 0x00, p2, data=pin_bytes)
            if sw1 == 0x90:
                return True
            elif sw1 == 0x63:
                raise AuthenticationError("Incorrect PIN", retries_remaining=sw2 & 0x0F)
            else:
                raise CommunicationError(f"HSM login failed: {sw1:02X}{sw2:02X}")
        except AuthenticationError:
            raise
        except CommunicationError:
            raise
        except Exception as e:
            raise CommunicationError(f"HSM login failed: {e}") from e

    def initialize(self, admin_pin: str, user_pin: str, label: Optional[str] = None) -> bool:
        """Initialize the HSM applet and set its PINs.

        Follows the SmartCard-HSM initialization lifecycle:
        1. INITIALIZE APPLET (00 28 00 00) resets the applet to a fresh
           state with default retry counters. This is destructive: all
           existing keys are lost.
        2. Set the SO PIN (PW2) and user PIN (PW1) via CHANGE REFERENCE DATA.

        Args:
            admin_pin: Security Officer (admin) PIN.
            user_pin: User PIN.
            label: Optional device label (stored as issuer DO when supported).
            
        Returns:
            True if initialization succeeded.
            
        Raises:
            ValueError: If PINs are too short.
            CommunicationError: If any step fails.
        """
        self._ensure_selected()
        
        if len(admin_pin) < 8:
            raise ValueError("Admin PIN must be at least 8 characters")
        if len(user_pin) < 4:
            raise ValueError("User PIN must be at least 4 characters")
        
        logger.warning("Initializing HSM applet. Any existing keys will be lost.")
        
        try:
            # 1. INITIALIZE APPLET with device operator key attempts + lifecycle
            init_data = bytes([0x03]) # Device operator key encryption attempts
            if label:
                label_bytes = label.encode("utf-8")[:16]
                init_data += label_bytes
            
            _, sw1, sw2 = self._device._transport.send_apdu(
                0x00, 0x28, 0x00, 0x00, data=init_data
            )
            if sw1 != 0x90:
                raise CommunicationError(f"HSM initialize failed: {sw1:02X}{sw2:02X}")
            
            # 2. Set PINs: PW3 (SO/admin) first, then PW1 (user)
            for p2, pin in ((0x82, admin_pin), (0x81, user_pin)):
                pin_bytes = pin.encode("utf-8")
                _, sw1, sw2 = self._device._transport.send_apdu(
                    0x00, 0x24, 0x00, p2, data=pin_bytes
                )
                if sw1 != 0x90:
                    role = "admin" if p2 == 0x82 else "user"
                    raise CommunicationError(
                        f"Failed to set {role} PIN: {sw1:02X}{sw2:02X}"
                    )
            
            logger.info("HSM initialized successfully")
            return True
        except Exception as e:
            if not isinstance(e, (ValueError, CommunicationError)):
                raise CommunicationError(f"HSM initialization failed: {e}") from e
            raise


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
    
    def get_pq_algorithms(self) -> dict[str, PQAlgorithm]:
        """Get list of supported post-quantum algorithms.
        
        Returns:
            Dictionary of algorithm name to PQAlgorithm spec.
        """
        return PQ_ALGORITHMS.copy()
    
    def generate_pq_key(
        self,
        slot: int,
        algorithm: str,
        label: Optional[str] = None,
    ) -> KeyInfo:
        """Generate a post-quantum key pair.
        
        Args:
            slot: Key slot number.
            algorithm: PQ algorithm name (e.g., "ml-kem-768", "ml-dsa-65").
            label: Optional label for the key.
            
        Returns:
            KeyInfo with key details.
            
        Raises:
            ValueError: If algorithm is not supported.
            NotImplementedError: If PQ key generation is not yet implemented.
        """
        if algorithm not in PQ_ALGORITHMS:
            raise ValueError(
                f"Unsupported PQ algorithm: {algorithm}. "
                f"Supported: {list(PQ_ALGORITHMS.keys())}"
            )
        
        # Check if firmware supports PQ (future feature)
        # For now, this is a placeholder for when hsm.py in SDK is mature
        logger.warning(
            f"PQ key generation for {algorithm} is planned but not yet implemented. "
            "Waiting for pico-keys-sdk hsm.py module to mature."
        )
        
        raise NotImplementedError(
            f"Post-quantum key generation ({algorithm}) is not yet implemented. "
            "This feature will be available when the pico-keys-sdk HSM module matures. "
            "See INTEGRACAO_PYPIKOKEY_SDK.md for roadmap details."
        )
    
    def encapsulate(self, slot: int, public_key: bytes) -> tuple[bytes, bytes]:
        """Encapsulate a shared secret using a KEM (Key Encapsulation Mechanism).
        
        Args:
            slot: Public key slot.
            public_key: Recipient's public key.
            
        Returns:
            Tuple of (ciphertext, shared_secret).
            
        Raises:
            NotImplementedError: If KEM operations are not yet implemented.
        """
        raise NotImplementedError(
            "Post-quantum KEM encapsulation is not yet implemented. "
            "This feature requires the pico-keys-sdk HSM module to support ML-KEM."
        )
    
    def decapsulate(self, slot: int, ciphertext: bytes) -> bytes:
        """Decapsulate a shared secret using a KEM.
        
        Args:
            slot: Private key slot.
            ciphertext: Ciphertext from encapsulation.
            
        Returns:
            Shared secret.
            
        Raises:
            NotImplementedError: If KEM operations are not yet implemented.
        """
        raise NotImplementedError(
            "Post-quantum KEM decapsulation is not yet implemented. "
            "This feature requires the pico-keys-sdk HSM module to support ML-KEM."
        )
    
    def sign_pq(self, slot: int, data: bytes, algorithm: str) -> bytes:
        """Sign data using a post-quantum signature algorithm.
        
        Args:
            slot: Private key slot.
            data: Data to sign.
            algorithm: PQ signature algorithm (e.g., "ml-dsa-65").
            
        Returns:
            Signature bytes.
            
        Raises:
            NotImplementedError: If PQ signatures are not yet implemented.
        """
        if algorithm not in PQ_ALGORITHMS:
            raise ValueError(f"Unsupported PQ algorithm: {algorithm}")
        
        algo_spec = PQ_ALGORITHMS[algorithm]
        if algo_spec.family != "Signature":
            raise ValueError(f"{algorithm} is not a signature algorithm")
        
        raise NotImplementedError(
            f"Post-quantum signatures ({algorithm}) are not yet implemented. "
            "This feature requires the pico-keys-sdk HSM module to support ML-DSA or SLH-DSA."
        )
    
    def verify_pq(self, public_key: bytes, data: bytes, signature: bytes, algorithm: str) -> bool:
        """Verify a post-quantum signature.
        
        Args:
            public_key: Signer's public key.
            data: Original data.
            signature: Signature to verify.
            algorithm: PQ signature algorithm used.
            
        Returns:
            True if signature is valid.
            
        Raises:
            NotImplementedError: If PQ verification is not yet implemented.
        """
        raise NotImplementedError(
            "Post-quantum signature verification is not yet implemented. "
            "This feature requires the pico-keys-sdk HSM module to support ML-DSA or SLH-DSA."
        )

    def __repr__(self) -> str:
        return f"HSMModule({self._device.name})"
