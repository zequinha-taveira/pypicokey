"""
USB transport for pypicokey.

This module provides raw USB transport for communicating with devices
in bootloader mode or for low-level USB operations.
"""

from typing import Optional
import logging

from pypicokey.device import BaseTransport
from pypicokey.constants import DEFAULT_TIMEOUT
from pypicokey.exceptions import TransportError, CommunicationError

logger = logging.getLogger(__name__)


class USBTransport(BaseTransport):
    """Raw USB transport for bootloader communication.
    
    This transport is used for devices in bootloader mode or for
    low-level USB bulk transfer operations.
    
    Example:
        >>> transport = USBTransport(vid=0x20A0, pid=0x42E1)
        >>> transport.open()
        >>> transport.send(boot_command)
        >>> response = transport.receive()
        >>> transport.close()
    """
    
    def __init__(
        self,
        vendor_id: int,
        product_id: int,
        interface: int = 0,
        endpoint_in: Optional[int] = None,
        endpoint_out: Optional[int] = None,
    ) -> None:
        """Initialize USB transport.
        
        Args:
            vendor_id: USB vendor ID.
            product_id: USB product ID.
            interface: USB interface number (default: 0).
            endpoint_in: Input endpoint address (auto-detected if None).
            endpoint_out: Output endpoint address (auto-detected if None).
        """
        self._vendor_id = vendor_id
        self._product_id = product_id
        self._interface = interface
        self._endpoint_in = endpoint_in
        self._endpoint_out = endpoint_out
        self._device: Optional[object] = None
        self._is_open = False
    
    @property
    def is_open(self) -> bool:
        """Check if transport is open."""
        return self._is_open and self._device is not None
    
    def open(self) -> None:
        """Open the USB connection.
        
        Finds the device, claims the interface, and sets up endpoints.
        
        Raises:
            TransportError: If connection fails.
        """
        if self._is_open:
            return
        
        try:
            import usb.core
            import usb.util
            
            # Find the device
            self._device = usb.core.find(
                idVendor=self._vendor_id,
                idProduct=self._product_id,
            )
            
            if self._device is None:
                raise TransportError(
                    f"USB device not found: {self._vendor_id:04X}:{self._product_id:04X}",
                    transport_type="USB",
                )
            
            # Detach kernel driver if necessary (Linux)
            try:
                if self._device.is_kernel_driver_active(self._interface):
                    self._device.detach_kernel_driver(self._interface)
            except (AttributeError, NotImplementedError):
                pass  # Not supported on this platform
            
            # Set configuration
            try:
                self._device.set_configuration()
            except usb.core.USBError:
                pass  # Configuration might already be set
            
            # Claim the interface
            usb.util.claim_interface(self._device, self._interface)
            
            # Auto-detect endpoints if not specified
            if self._endpoint_in is None or self._endpoint_out is None:
                self._detect_endpoints()
            
            self._is_open = True
            logger.debug(
                f"Opened USB device: {self._vendor_id:04X}:{self._product_id:04X}"
            )
            
        except ImportError:
            raise TransportError("pyusb library not installed", transport_type="USB")
        except TransportError:
            raise
        except Exception as e:
            self._is_open = False
            raise TransportError(f"Failed to open USB device: {e}", transport_type="USB") from e
    
    def close(self) -> None:
        """Close the USB connection."""
        if self._device:
            try:
                import usb.util
                usb.util.release_interface(self._device, self._interface)
                usb.util.dispose_resources(self._device)
                logger.debug("Closed USB device")
            except Exception as e:
                logger.warning(f"Error closing USB device: {e}")
            finally:
                self._device = None
                self._is_open = False
    
    def send(self, data: bytes) -> None:
        """Send data via USB bulk transfer.
        
        Args:
            data: Data bytes to send.
            
        Raises:
            TransportError: If not connected or endpoint not configured.
            CommunicationError: If send fails.
        """
        if not self.is_open or self._device is None:
            raise TransportError("USB device not open", transport_type="USB")
        
        if self._endpoint_out is None:
            raise TransportError("Output endpoint not configured", transport_type="USB")
        
        try:
            bytes_written = self._device.write(
                self._endpoint_out,
                data,
                timeout=int(DEFAULT_TIMEOUT * 1000),
            )
            
            logger.debug(f"Sent {bytes_written} bytes via USB")
            
        except Exception as e:
            raise CommunicationError(f"Failed to send USB data: {e}") from e
    
    def receive(self, timeout: Optional[float] = None) -> bytes:
        """Receive data via USB bulk transfer.
        
        Args:
            timeout: Read timeout in seconds (default: DEFAULT_TIMEOUT).
            
        Returns:
            Received data bytes.
            
        Raises:
            TransportError: If not connected or endpoint not configured.
            CommunicationError: If receive fails or times out.
        """
        if not self.is_open or self._device is None:
            raise TransportError("USB device not open", transport_type="USB")
        
        if self._endpoint_in is None:
            raise TransportError("Input endpoint not configured", transport_type="USB")
        
        timeout_ms = int((timeout or DEFAULT_TIMEOUT) * 1000)
        
        try:
            data = self._device.read(
                self._endpoint_in,
                4096,  # Max read size
                timeout=timeout_ms,
            )
            
            result = bytes(data)
            logger.debug(f"Received {len(result)} bytes via USB")
            return result
            
        except Exception as e:
            if "timeout" in str(e).lower():
                raise CommunicationError("USB read timeout") from e
            raise CommunicationError(f"Failed to receive USB data: {e}") from e
    
    def control_transfer(
        self,
        request_type: int,
        request: int,
        value: int = 0,
        index: int = 0,
        data: Optional[bytes] = None,
        length: int = 0,
    ) -> bytes:
        """Perform a USB control transfer.
        
        Args:
            request_type: bmRequestType field.
            request: bRequest field.
            value: wValue field.
            index: wIndex field.
            data: Data to send (for OUT transfers).
            length: Number of bytes to receive (for IN transfers).
            
        Returns:
            Response data for IN transfers, empty bytes for OUT.
            
        Raises:
            TransportError: If not connected.
            CommunicationError: If transfer fails.
        """
        if not self.is_open or self._device is None:
            raise TransportError("USB device not open", transport_type="USB")
        
        try:
            result = self._device.ctrl_transfer(
                request_type,
                request,
                value,
                index,
                data or length,
                timeout=int(DEFAULT_TIMEOUT * 1000),
            )
            
            return bytes(result) if result else bytes()
            
        except Exception as e:
            raise CommunicationError(f"Control transfer failed: {e}") from e
    
    def _detect_endpoints(self) -> None:
        """Auto-detect bulk endpoints on the interface.
        
        Raises:
            TransportError: If endpoints cannot be detected.
        """
        import usb.util
        
        cfg = self._device.get_active_configuration()
        intf = cfg[(self._interface, 0)]
        
        # Find bulk OUT endpoint
        ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress)
            == usb.util.ENDPOINT_OUT
            and usb.util.endpoint_type(e.bmAttributes)
            == usb.util.ENDPOINT_TYPE_BULK,
        )
        
        # Find bulk IN endpoint
        ep_in = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress)
            == usb.util.ENDPOINT_IN
            and usb.util.endpoint_type(e.bmAttributes)
            == usb.util.ENDPOINT_TYPE_BULK,
        )
        
        if ep_out:
            self._endpoint_out = ep_out.bEndpointAddress
        if ep_in:
            self._endpoint_in = ep_in.bEndpointAddress
        
        logger.debug(f"Detected endpoints: IN={self._endpoint_in}, OUT={self._endpoint_out}")
    
    def __repr__(self) -> str:
        """Return string representation."""
        status = "open" if self._is_open else "closed"
        return f"USBTransport({self._vendor_id:04X}:{self._product_id:04X}, {status})"
