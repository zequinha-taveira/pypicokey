"""
HID transport for pypicokey.

This module provides HID (Human Interface Device) transport for 
communicating with FIDO2/U2F devices.
"""

from typing import Optional
import logging

from pypicokey.device import BaseTransport
from pypicokey.constants import HID_PACKET_SIZE, HID_READ_TIMEOUT
from pypicokey.exceptions import TransportError, CommunicationError

logger = logging.getLogger(__name__)


class HIDTransport(BaseTransport):
    """HID transport for FIDO2/U2F communication.
    
    This transport is used for devices that expose a HID interface,
    typically FIDO2/U2F security keys.
    
    Example:
        >>> transport = HIDTransport("/dev/hidraw0", vid=0x20A0, pid=0x42B2)
        >>> transport.open()
        >>> transport.send(ctap_command)
        >>> response = transport.receive()
        >>> transport.close()
    """
    
    def __init__(
        self,
        path: str,
        vendor_id: int,
        product_id: int,
        packet_size: int = HID_PACKET_SIZE,
    ) -> None:
        """Initialize HID transport.
        
        Args:
            path: OS-specific device path.
            vendor_id: USB vendor ID.
            product_id: USB product ID.
            packet_size: HID packet size (default: 64 bytes).
        """
        self._path = path
        self._vendor_id = vendor_id
        self._product_id = product_id
        self._packet_size = packet_size
        self._device: Optional[object] = None
        self._is_open = False
    
    @property
    def is_open(self) -> bool:
        """Check if transport is open."""
        return self._is_open and self._device is not None
    
    def open(self) -> None:
        """Open the HID connection.
        
        Raises:
            TransportError: If connection fails.
        """
        if self._is_open:
            return
        
        try:
            import hid
            
            self._device = hid.device()
            
            if self._path:
                # Open by path (preferred)
                self._device.open_path(self._path.encode())
            else:
                # Open by VID/PID
                self._device.open(self._vendor_id, self._product_id)
            
            # Set non-blocking mode for reads
            self._device.set_nonblocking(False)
            
            self._is_open = True
            logger.debug(f"Opened HID device: {self._path or f'{self._vendor_id:04X}:{self._product_id:04X}'}")
            
        except ImportError:
            raise TransportError("hidapi library not installed", transport_type="HID")
        except Exception as e:
            self._is_open = False
            raise TransportError(f"Failed to open HID device: {e}", transport_type="HID") from e
    
    def close(self) -> None:
        """Close the HID connection."""
        if self._device:
            try:
                self._device.close()
                logger.debug("Closed HID device")
            except Exception as e:
                logger.warning(f"Error closing HID device: {e}")
            finally:
                self._device = None
                self._is_open = False
    
    def send(self, data: bytes) -> None:
        """Send data to the HID device.
        
        Data is automatically padded to the packet size if necessary.
        Large data is split into multiple packets.
        
        Args:
            data: Data bytes to send.
            
        Raises:
            TransportError: If not connected.
            CommunicationError: If send fails.
        """
        if not self.is_open or self._device is None:
            raise TransportError("HID device not open", transport_type="HID")
        
        try:
            # Prepend report ID (0x00 for default)
            packet = bytes([0x00]) + data
            
            # Pad to packet size if necessary
            if len(packet) < self._packet_size + 1:
                packet = packet + bytes(self._packet_size + 1 - len(packet))
            
            bytes_written = self._device.write(packet)
            
            if bytes_written < 0:
                raise CommunicationError("HID write failed")
            
            logger.debug(f"Sent {bytes_written} bytes via HID")
            
        except CommunicationError:
            raise
        except Exception as e:
            raise CommunicationError(f"Failed to send HID data: {e}") from e
    
    def receive(self, timeout: Optional[float] = None) -> bytes:
        """Receive data from the HID device.
        
        Args:
            timeout: Read timeout in seconds (default: HID_READ_TIMEOUT).
            
        Returns:
            Received data bytes.
            
        Raises:
            TransportError: If not connected.
            CommunicationError: If receive fails or times out.
        """
        if not self.is_open or self._device is None:
            raise TransportError("HID device not open", transport_type="HID")
        
        timeout_ms = int((timeout or HID_READ_TIMEOUT) * 1000)
        
        try:
            data = self._device.read(self._packet_size, timeout_ms)
            
            if not data:
                raise CommunicationError("HID read timeout")
            
            result = bytes(data)
            logger.debug(f"Received {len(result)} bytes via HID")
            return result
            
        except CommunicationError:
            raise
        except Exception as e:
            raise CommunicationError(f"Failed to receive HID data: {e}") from e
    
    def exchange(self, data: bytes, timeout: Optional[float] = None) -> bytes:
        """Send data and receive response.
        
        Convenience method that combines send() and receive().
        
        Args:
            data: Data bytes to send.
            timeout: Read timeout in seconds.
            
        Returns:
            Response bytes.
        """
        self.send(data)
        return self.receive(timeout)
    
    def __repr__(self) -> str:
        """Return string representation."""
        status = "open" if self._is_open else "closed"
        return f"HIDTransport({self._vendor_id:04X}:{self._product_id:04X}, {status})"
