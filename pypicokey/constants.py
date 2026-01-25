"""
Constants for pypicokey.

This module contains USB vendor/product IDs, enums, and other constants
used throughout the library.
"""

from enum import Enum, IntEnum


class VendorID:
    """USB Vendor IDs for PicoKey devices."""
    
    # Raspberry Pi Foundation (used by some Pico-based devices)
    RASPBERRY_PI = 0x2E8A
    
    # PicoKeys vendor ID
    PICOKEYS = 0x20A0
    
    # Generic HID vendor (for development/testing)
    GENERIC = 0x0000

    # Community vendor ID (for Pico Key Web)
    COMMUNITY = 0xFEFF


class ProductID:
    """USB Product IDs for PicoKey devices."""
    
    # Pico FIDO2 devices
    PICO_FIDO = 0x42B2
    PICO_FIDO_PLUS = 0x42B3
    
    # Pico OpenPGP devices
    PICO_OPENPGP = 0x42C1
    
    # Pico HSM devices
    PICO_HSM = 0x42D1
    PICO_HSM_PLUS = 0x42D2
    
    # Pico Boot (bootloader mode)
    PICO_BOOT = 0x42E1
    
    # Development/unknown
    UNKNOWN = 0x0000
    PICO_KEY_WEB = 0xFCFD


class DeviceMode(str, Enum):
    """Operating modes for PicoKey devices."""
    
    # FIDO2/U2F mode (HID interface)
    FIDO = "fido"
    
    # OpenPGP smartcard mode (CCID interface)
    OPENPGP = "openpgp"
    
    # Hardware Security Module mode (CCID interface)
    HSM = "hsm"
    
    # Bootloader mode for firmware updates
    BOOT = "boot"
    
    # Unknown or unrecognized mode
    UNKNOWN = "unknown"
    
    def __str__(self) -> str:
        return self.value


class TransportType(str, Enum):
    """Transport layer types for device communication."""
    
    # USB Human Interface Device
    HID = "hid"
    
    # Chip Card Interface Device (smartcard)
    CCID = "ccid"
    
    # Raw USB (for bootloader)
    USB = "usb"
    
    # Unknown transport
    UNKNOWN = "unknown"
    
    def __str__(self) -> str:
        return self.value


class InterfaceClass(IntEnum):
    """USB interface classes."""
    
    # Human Interface Device (HID)
    HID = 0x03
    
    # Smart Card / CCID
    CCID = 0x0B
    
    # Mass Storage (for bootloader)
    MASS_STORAGE = 0x08
    
    # Vendor-specific
    VENDOR = 0xFF


# Known PicoKey device configurations
# Format: (vendor_id, product_id) -> (device_name, default_mode)
KNOWN_DEVICES: dict[tuple[int, int], tuple[str, DeviceMode]] = {
    (VendorID.PICOKEYS, ProductID.PICO_FIDO): ("Pico FIDO", DeviceMode.FIDO),
    (VendorID.PICOKEYS, ProductID.PICO_FIDO_PLUS): ("Pico FIDO Plus", DeviceMode.FIDO),
    (VendorID.PICOKEYS, ProductID.PICO_OPENPGP): ("Pico OpenPGP", DeviceMode.OPENPGP),
    (VendorID.PICOKEYS, ProductID.PICO_HSM): ("Pico HSM", DeviceMode.HSM),
    (VendorID.PICOKEYS, ProductID.PICO_HSM_PLUS): ("Pico HSM Plus", DeviceMode.HSM),
    (VendorID.PICOKEYS, ProductID.PICO_BOOT): ("Pico Boot", DeviceMode.BOOT),
    # Pico Key Community/Web Interface
    (VendorID.COMMUNITY, ProductID.PICO_KEY_WEB): ("Pico Key", DeviceMode.FIDO),
}


# FIDO2 CTAP constants
class CTAPCommand(IntEnum):
    """CTAP2 command bytes."""
    
    AUTHENTICATOR_MAKE_CREDENTIAL = 0x01
    AUTHENTICATOR_GET_ASSERTION = 0x02
    AUTHENTICATOR_GET_INFO = 0x04
    AUTHENTICATOR_CLIENT_PIN = 0x06
    AUTHENTICATOR_RESET = 0x07
    AUTHENTICATOR_GET_NEXT_ASSERTION = 0x08
    AUTHENTICATOR_CREDENTIAL_MANAGEMENT = 0x0A
    AUTHENTICATOR_SELECTION = 0x0B
    AUTHENTICATOR_CONFIG = 0x0D


# OpenPGP APDU constants
class OpenPGPInstruction(IntEnum):
    """OpenPGP APDU instruction bytes."""
    
    SELECT = 0xA4
    VERIFY = 0x20
    CHANGE_PIN = 0x24
    RESET_RETRY_COUNTER = 0x2C
    GET_DATA = 0xCA
    PUT_DATA = 0xDA
    GENERATE_KEY = 0x47
    COMPUTE_SIGNATURE = 0x2A
    DECIPHER = 0x2A
    INTERNAL_AUTHENTICATE = 0x88
    GET_RESPONSE = 0xC0


# HSM constants
class HSMState(str, Enum):
    """HSM device states."""
    
    UNINITIALIZED = "uninitialized"
    INITIALIZED = "initialized"
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    
    def __str__(self) -> str:
        return self.value


# Default timeouts (in seconds)
DEFAULT_TIMEOUT = 5.0
HID_READ_TIMEOUT = 3.0
CCID_READ_TIMEOUT = 10.0


# Buffer sizes
HID_PACKET_SIZE = 64
CCID_MAX_RESPONSE = 65536
