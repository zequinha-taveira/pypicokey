"""
pypicokey - Open-source Python library for managing PicoKey devices.

This library provides a high-level API for interacting with PicoKey devices
including Pico FIDO, Pico OpenPGP, Pico HSM, and Pico Boot.

Example:
    >>> from pypicokey import PicoKeyManager
    >>> manager = PicoKeyManager()
    >>> devices = manager.discover()
    >>> for device in devices:
    ...     print(f"Found: {device.name} ({device.mode})")
"""

__version__ = "0.1.0"
__author__ = "PicoKey Community Contributors"

# Public API
from pypicokey.manager import PicoKeyManager
from pypicokey.device import PicoKeyDevice, DeviceInfo
from pypicokey.constants import DeviceMode, VendorID, ProductID
from pypicokey.exceptions import (
    PicoKeyError,
    DeviceNotFoundError,
    ConnectionError,
    CommunicationError,
    UnsupportedModeError,
)

__all__ = [
    # Version
    "__version__",
    # Manager
    "PicoKeyManager",
    # Device
    "PicoKeyDevice",
    "DeviceInfo",
    # Constants
    "DeviceMode",
    "VendorID",
    "ProductID",
    # Exceptions
    "PicoKeyError",
    "DeviceNotFoundError",
    "ConnectionError",
    "CommunicationError",
    "UnsupportedModeError",
]
