"""
Tests for the exceptions module.
"""

import pytest

from pypicokey.exceptions import (
    PicoKeyError,
    DeviceNotFoundError,
    ConnectionError,
    CommunicationError,
    UnsupportedModeError,
    TransportError,
    AuthenticationError,
    ProvisioningError,
)


class TestPicoKeyError:
    """Tests for base PicoKeyError."""
    
    def test_simple_message(self) -> None:
        """Test exception with simple message."""
        error = PicoKeyError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.details is None
    
    def test_message_with_details(self) -> None:
        """Test exception with message and details."""
        error = PicoKeyError("Operation failed", details="Timeout occurred")
        assert str(error) == "Operation failed: Timeout occurred"
        assert error.message == "Operation failed"
        assert error.details == "Timeout occurred"
    
    def test_inheritance(self) -> None:
        """Test that PicoKeyError inherits from Exception."""
        error = PicoKeyError("Test")
        assert isinstance(error, Exception)


class TestDeviceNotFoundError:
    """Tests for DeviceNotFoundError."""
    
    def test_default_message(self) -> None:
        """Test default error message."""
        error = DeviceNotFoundError()
        assert "No PicoKey device found" in str(error)
    
    def test_custom_message(self) -> None:
        """Test custom error message."""
        error = DeviceNotFoundError("Device disconnected")
        assert "Device disconnected" in str(error)
    
    def test_with_serial_number(self) -> None:
        """Test error with serial number."""
        error = DeviceNotFoundError("Device not found", serial_number="ABC123")
        assert "ABC123" in str(error)
        assert error.serial_number == "ABC123"
    
    def test_inheritance(self) -> None:
        """Test inheritance from PicoKeyError."""
        error = DeviceNotFoundError()
        assert isinstance(error, PicoKeyError)


class TestConnectionError:
    """Tests for ConnectionError."""
    
    def test_default_message(self) -> None:
        """Test default error message."""
        error = ConnectionError()
        assert "Failed to connect" in str(error)
    
    def test_with_device_path(self) -> None:
        """Test error with device path."""
        error = ConnectionError("Access denied", device_path="/dev/hidraw0")
        assert "/dev/hidraw0" in str(error)
        assert error.device_path == "/dev/hidraw0"


class TestCommunicationError:
    """Tests for CommunicationError."""
    
    def test_default_message(self) -> None:
        """Test default error message."""
        error = CommunicationError()
        assert "Communication" in str(error)
    
    def test_with_command(self) -> None:
        """Test error with command info."""
        error = CommunicationError("Timeout", command="GET_INFO")
        assert "GET_INFO" in str(error)
        assert error.command == "GET_INFO"
    
    def test_with_response_code(self) -> None:
        """Test error with response code."""
        error = CommunicationError("Failed", response_code=0x6985)
        assert "6985" in str(error).upper()
        assert error.response_code == 0x6985


class TestUnsupportedModeError:
    """Tests for UnsupportedModeError."""
    
    def test_default_message(self) -> None:
        """Test default error message."""
        error = UnsupportedModeError()
        assert "not supported" in str(error)
    
    def test_with_modes(self) -> None:
        """Test error with mode information."""
        error = UnsupportedModeError(
            "Operation not supported",
            current_mode="fido",
            required_mode="hsm",
        )
        assert "fido" in str(error)
        assert "hsm" in str(error)
        assert error.current_mode == "fido"
        assert error.required_mode == "hsm"


class TestTransportError:
    """Tests for TransportError."""
    
    def test_default_message(self) -> None:
        """Test default error message."""
        error = TransportError()
        assert "Transport" in str(error)
    
    def test_with_transport_type(self) -> None:
        """Test error with transport type."""
        error = TransportError("Failed to open", transport_type="HID")
        assert "HID" in str(error)
        assert error.transport_type == "HID"


class TestAuthenticationError:
    """Tests for AuthenticationError."""
    
    def test_default_message(self) -> None:
        """Test default error message."""
        error = AuthenticationError()
        assert "Authentication" in str(error)
    
    def test_with_retries(self) -> None:
        """Test error with retry count."""
        error = AuthenticationError("PIN incorrect", retries_remaining=2)
        assert "2" in str(error)
        assert error.retries_remaining == 2


class TestProvisioningError:
    """Tests for ProvisioningError."""
    
    def test_default_message(self) -> None:
        """Test default error message."""
        error = ProvisioningError()
        assert "Provisioning" in str(error)
    
    def test_with_stage(self) -> None:
        """Test error with provisioning stage."""
        error = ProvisioningError("Initialization failed", stage="key_generation")
        assert "key_generation" in str(error)
        assert error.stage == "key_generation"


class TestExceptionHierarchy:
    """Tests for exception hierarchy."""
    
    def test_all_inherit_from_picokey_error(self) -> None:
        """Test that all custom exceptions inherit from PicoKeyError."""
        exceptions = [
            DeviceNotFoundError(),
            ConnectionError(),
            CommunicationError(),
            UnsupportedModeError(),
            TransportError(),
            AuthenticationError(),
            ProvisioningError(),
        ]
        
        for exc in exceptions:
            assert isinstance(exc, PicoKeyError), f"{type(exc).__name__} should inherit from PicoKeyError"
    
    def test_catch_all_with_base_class(self) -> None:
        """Test catching all pypicokey exceptions with base class."""
        def raise_various_errors(error_type: str) -> None:
            if error_type == "device":
                raise DeviceNotFoundError()
            elif error_type == "connection":
                raise ConnectionError()
            elif error_type == "communication":
                raise CommunicationError()
        
        for error_type in ["device", "connection", "communication"]:
            with pytest.raises(PicoKeyError):
                raise_various_errors(error_type)


class TestPublicExports:
    """Callers must be able to import the full exception taxonomy from pypicokey."""

    def test_all_contains_exception_names(self) -> None:
        import pypicokey

        expected = {
            "PicoKeyError",
            "DeviceNotFoundError",
            "DeviceConnectionError",
            "ConnectionError",
            "CommunicationError",
            "UnsupportedModeError",
            "TransportError",
            "AuthenticationError",
            "ProvisioningError",
        }
        assert expected.issubset(set(pypicokey.__all__))

    def test_exported_exceptions_are_catchable_from_package_root(self) -> None:
        import pypicokey
        from pypicokey.exceptions import DeviceConnectionError

        assert pypicokey.TransportError is TransportError
        assert pypicokey.AuthenticationError is AuthenticationError
        assert pypicokey.ProvisioningError is ProvisioningError
        # Backwards-compatible alias and canonical name both exported
        assert pypicokey.ConnectionError is DeviceConnectionError
