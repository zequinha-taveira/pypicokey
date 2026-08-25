"""
Device abstraction for pypicokey.

This module provides the PicoKeyDevice class, which represents a connected
PicoKey device and provides methods for interacting with it.
"""

from dataclasses import dataclass, field
from typing import Optional, Any
from abc import ABC, abstractmethod

from pypicokey.constants import (
    DeviceMode,
    TransportType,
    VendorID,
    ProductID,
    KNOWN_DEVICES,
)
from pypicokey.exceptions import (
    DeviceConnectionError,
    CommunicationError,
    UnsupportedModeError,
)


@dataclass
class DeviceInfo:
    """Information about a PicoKey device.
    
    This dataclass contains all relevant information about a connected
    PicoKey device, including hardware identifiers and firmware details.
    
    Attributes:
        vendor_id: USB Vendor ID.
        product_id: USB Product ID.
        name: Human-readable device name.
        mode: Current operating mode (FIDO, OpenPGP, HSM, Boot).
        serial_number: Device serial number.
        firmware_version: Firmware version string.
        transport_type: Transport layer type (HID, CCID, USB).
        path: OS-specific device path.
        manufacturer: Manufacturer string.
        product: Product string.
    """
    
    vendor_id: int
    product_id: int
    name: str
    mode: DeviceMode
    serial_number: Optional[str] = None
    firmware_version: Optional[str] = None
    transport_type: TransportType = TransportType.UNKNOWN
    path: Optional[str] = None
    manufacturer: Optional[str] = None
    product: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        """Return a human-readable string representation."""
        parts = [f"{self.name} ({self.mode})"]
        if self.serial_number:
            parts.append(f"S/N: {self.serial_number}")
        if self.firmware_version:
            parts.append(f"FW: {self.firmware_version}")
        return " | ".join(parts)
    
    @property
    def vendor_id_hex(self) -> str:
        """Return vendor ID as hex string."""
        return f"0x{self.vendor_id:04X}"
    
    @property
    def product_id_hex(self) -> str:
        """Return product ID as hex string."""
        return f"0x{self.product_id:04X}"
    
    def is_picokey(self) -> bool:
        """Check if this is a known PicoKey device."""
        return (self.vendor_id, self.product_id) in KNOWN_DEVICES


class BaseTransport(ABC):
    """Abstract base class for device transports.
    
    This class defines the interface that all transport implementations
    (HID, CCID, USB) must implement.
    """
    
    @abstractmethod
    def open(self) -> None:
        """Open the transport connection."""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the transport connection."""
        pass
    
    @abstractmethod
    def send(self, data: bytes) -> None:
        """Send data to the device."""
        pass
    
    @abstractmethod
    def receive(self, timeout: Optional[float] = None) -> bytes:
        """Receive data from the device."""
        pass
    
    @property
    @abstractmethod
    def is_open(self) -> bool:
        """Check if the transport is open."""
        pass


class PicoKeyDevice:
    """Represents a connected PicoKey device.
    
    This class provides high-level methods for interacting with a PicoKey
    device, abstracting away the transport layer details.
    
    Example:
        >>> device = PicoKeyDevice(device_info)
        >>> device.connect()
        >>> info = device.get_info()
        >>> print(f"Firmware: {info.firmware_version}")
        >>> device.disconnect()
    """
    
    def __init__(self, info: DeviceInfo) -> None:
        """Initialize a PicoKeyDevice.
        
        Args:
            info: Device information from discovery.
        """
        self._info = info
        self._transport: Optional[BaseTransport] = None
        self._connected = False
    
    @property
    def info(self) -> DeviceInfo:
        """Get device information."""
        return self._info
    
    @property
    def name(self) -> str:
        """Get device name."""
        return self._info.name
    
    @property
    def mode(self) -> DeviceMode:
        """Get current device mode."""
        return self._info.mode
    
    @property
    def vendor_id(self) -> int:
        """Get USB vendor ID."""
        return self._info.vendor_id
    
    @property
    def product_id(self) -> int:
        """Get USB product ID."""
        return self._info.product_id
    
    @property
    def serial_number(self) -> Optional[str]:
        """Get device serial number."""
        return self._info.serial_number
    
    @property
    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self._connected and self._transport is not None and self._transport.is_open
    
    def connect(self) -> None:
        """Connect to the device.
        
        Opens the transport layer connection to the device.
        
        Raises:
            DeviceConnectionError: If connection fails.
        """
        if self._connected:
            return
        
        try:
            self._transport = self._create_transport()
            self._transport.open()
            self._connected = True
        except Exception as e:
            self._connected = False
            raise DeviceConnectionError(
                f"Failed to connect to {self.name}",
                device_path=self._info.path,
            ) from e
    
    def disconnect(self) -> None:
        """Disconnect from the device.
        
        Closes the transport layer connection.
        """
        if self._transport:
            try:
                self._transport.close()
            except Exception:
                pass  # Ignore errors during disconnect
        self._transport = None
        self._connected = False
    
    def get_info(self) -> DeviceInfo:
        """Get current device information.
        
        Returns updated device information, potentially querying the
        device for runtime details like firmware version.
        
        Returns:
            DeviceInfo with current device state.
        """
        # For now, return cached info
        # TODO: Query device for runtime information
        return self._info
    
    def send_command(self, data: bytes) -> bytes:
        """Send a raw command to the device.
        
        This is a low-level method for sending raw bytes to the device.
        Use module-specific methods for higher-level operations.
        
        Args:
            data: Raw command bytes to send.
            
        Returns:
            Response bytes from the device.
            
        Raises:
            DeviceConnectionError: If not connected.
            CommunicationError: If communication fails.
        """
        if not self.is_connected or self._transport is None:
            raise DeviceConnectionError("Not connected to device")
        
        try:
            self._transport.send(data)
            return self._transport.receive()
        except Exception as e:
            raise CommunicationError(
                "Failed to communicate with device",
                command=data.hex() if len(data) <= 32 else f"{data[:16].hex()}...",
            ) from e
    
    def _create_transport(self) -> BaseTransport:
        """Create the appropriate transport for this device.
        
        Returns:
            Transport instance for this device.
            
        Raises:
            UnsupportedModeError: If transport type is not supported.
        """
        # Import here to avoid circular imports
        from pypicokey.transport.hid import HIDTransport
        from pypicokey.transport.ccid import CCIDTransport
        from pypicokey.transport.usb import USBTransport
        from pypicokey.transport.msd import MSDTransport

        if self._info.transport_type == TransportType.HID:
            return HIDTransport(self._info.path or "", self._info.vendor_id, self._info.product_id)
        elif self._info.transport_type == TransportType.CCID:
            return CCIDTransport(self._info.path or "")
        elif self._info.transport_type == TransportType.USB:
            return USBTransport(self._info.vendor_id, self._info.product_id)
        elif self._info.transport_type == TransportType.MSD:
            return MSDTransport(self._info.path or None)
        else:
            raise UnsupportedModeError(
                "Unsupported transport type",
                current_mode=str(self._info.transport_type),
            )
    
    def __enter__(self) -> "PicoKeyDevice":
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.disconnect()
    
    def __repr__(self) -> str:
        """Return string representation."""
        status = "connected" if self._connected else "disconnected"
        return f"PicoKeyDevice({self.name}, {self.mode}, {status})"
    
    def __str__(self) -> str:
        """Return human-readable string."""
        return str(self._info)
