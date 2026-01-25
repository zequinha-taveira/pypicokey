"""
Custom exceptions for pypicokey.

This module defines all custom exceptions used throughout the library,
providing clear error messages and proper exception hierarchy.
"""

from typing import Optional


class PicoKeyError(Exception):
    """Base exception for all pypicokey errors.
    
    All custom exceptions in this library inherit from this class,
    making it easy to catch any pypicokey-related error.
    
    Example:
        >>> try:
        ...     device.connect()
        ... except PicoKeyError as e:
        ...     print(f"PicoKey error: {e}")
    """
    
    def __init__(self, message: str, details: Optional[str] = None) -> None:
        """Initialize the exception.
        
        Args:
            message: Human-readable error message.
            details: Optional additional details about the error.
        """
        self.message = message
        self.details = details
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """Format the exception message."""
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class DeviceNotFoundError(PicoKeyError):
    """Raised when a PicoKey device cannot be found.
    
    This exception is raised when:
    - No PicoKey devices are connected
    - A specific device (by serial number) is not found
    - The requested device type is not available
    
    Example:
        >>> devices = manager.discover()
        >>> if not devices:
        ...     raise DeviceNotFoundError("No PicoKey devices connected")
    """
    
    def __init__(
        self,
        message: str = "No PicoKey device found",
        serial_number: Optional[str] = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Human-readable error message.
            serial_number: Optional serial number of the device being searched.
        """
        self.serial_number = serial_number
        details = f"Serial: {serial_number}" if serial_number else None
        super().__init__(message, details)


class ConnectionError(PicoKeyError):
    """Raised when connection to a device fails.
    
    This exception is raised when:
    - Failed to open USB device handle
    - Device is already in use by another process
    - Permission denied accessing the device
    - Device disconnected during operation
    """
    
    def __init__(
        self,
        message: str = "Failed to connect to device",
        device_path: Optional[str] = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Human-readable error message.
            device_path: Optional device path that failed to connect.
        """
        self.device_path = device_path
        details = f"Path: {device_path}" if device_path else None
        super().__init__(message, details)


class CommunicationError(PicoKeyError):
    """Raised when communication with a device fails.
    
    This exception is raised when:
    - Send/receive operations fail
    - Timeout waiting for response
    - Invalid response received
    - Protocol error detected
    """
    
    def __init__(
        self,
        message: str = "Communication with device failed",
        command: Optional[str] = None,
        response_code: Optional[int] = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Human-readable error message.
            command: Optional command that caused the error.
            response_code: Optional response/error code from device.
        """
        self.command = command
        self.response_code = response_code
        
        details_parts = []
        if command:
            details_parts.append(f"Command: {command}")
        if response_code is not None:
            details_parts.append(f"Response code: 0x{response_code:04X}")
        
        details = ", ".join(details_parts) if details_parts else None
        super().__init__(message, details)


class UnsupportedModeError(PicoKeyError):
    """Raised when an operation is not supported in the current mode.
    
    This exception is raised when:
    - Trying to use FIDO commands on an OpenPGP device
    - Attempting HSM operations on a FIDO device
    - Operation not available in current device state
    """
    
    def __init__(
        self,
        message: str = "Operation not supported in current mode",
        current_mode: Optional[str] = None,
        required_mode: Optional[str] = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Human-readable error message.
            current_mode: The current device mode.
            required_mode: The mode required for the operation.
        """
        self.current_mode = current_mode
        self.required_mode = required_mode
        
        details_parts = []
        if current_mode:
            details_parts.append(f"Current: {current_mode}")
        if required_mode:
            details_parts.append(f"Required: {required_mode}")
        
        details = ", ".join(details_parts) if details_parts else None
        super().__init__(message, details)


class TransportError(PicoKeyError):
    """Raised when a transport layer error occurs.
    
    This exception is raised when:
    - HID transport fails to open
    - CCID smart card reader error
    - USB bulk transfer error
    """
    
    def __init__(
        self,
        message: str = "Transport layer error",
        transport_type: Optional[str] = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Human-readable error message.
            transport_type: The transport type (HID, CCID, USB).
        """
        self.transport_type = transport_type
        details = f"Transport: {transport_type}" if transport_type else None
        super().__init__(message, details)


class AuthenticationError(PicoKeyError):
    """Raised when authentication fails.
    
    This exception is raised when:
    - PIN verification fails
    - User presence check fails
    - Biometric verification fails
    """
    
    def __init__(
        self,
        message: str = "Authentication failed",
        retries_remaining: Optional[int] = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Human-readable error message.
            retries_remaining: Number of retries remaining before lockout.
        """
        self.retries_remaining = retries_remaining
        details = f"Retries remaining: {retries_remaining}" if retries_remaining is not None else None
        super().__init__(message, details)


class ProvisioningError(PicoKeyError):
    """Raised when device provisioning fails.
    
    This exception is raised when:
    - Device initialization fails
    - Key generation fails
    - Secure lock operation fails
    """
    
    def __init__(
        self,
        message: str = "Provisioning error",
        stage: Optional[str] = None,
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Human-readable error message.
            stage: The provisioning stage that failed.
        """
        self.stage = stage
        details = f"Stage: {stage}" if stage else None
        super().__init__(message, details)
