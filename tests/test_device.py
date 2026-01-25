"""
Tests for the device module.
"""

import pytest

from pypicokey.device import DeviceInfo, PicoKeyDevice
from pypicokey.constants import DeviceMode, TransportType, VendorID, ProductID


class TestDeviceInfo:
    """Tests for DeviceInfo dataclass."""
    
    def test_basic_creation(self) -> None:
        """Test creating a basic DeviceInfo."""
        info = DeviceInfo(
            vendor_id=VendorID.PICOKEYS,
            product_id=ProductID.PICO_FIDO,
            name="Pico FIDO",
            mode=DeviceMode.FIDO,
        )
        
        assert info.vendor_id == VendorID.PICOKEYS
        assert info.product_id == ProductID.PICO_FIDO
        assert info.name == "Pico FIDO"
        assert info.mode == DeviceMode.FIDO
    
    def test_full_creation(self) -> None:
        """Test creating a DeviceInfo with all fields."""
        info = DeviceInfo(
            vendor_id=VendorID.PICOKEYS,
            product_id=ProductID.PICO_HSM,
            name="Pico HSM",
            mode=DeviceMode.HSM,
            serial_number="ABC123",
            firmware_version="1.2.3",
            transport_type=TransportType.CCID,
            path="/dev/reader0",
            manufacturer="PicoKeys",
            product="HSM Device",
        )
        
        assert info.serial_number == "ABC123"
        assert info.firmware_version == "1.2.3"
        assert info.transport_type == TransportType.CCID
        assert info.manufacturer == "PicoKeys"
    
    def test_vendor_id_hex(self) -> None:
        """Test vendor_id_hex property."""
        info = DeviceInfo(
            vendor_id=0x20A0,
            product_id=0x42B2,
            name="Test",
            mode=DeviceMode.FIDO,
        )
        
        assert info.vendor_id_hex == "0x20A0"
    
    def test_product_id_hex(self) -> None:
        """Test product_id_hex property."""
        info = DeviceInfo(
            vendor_id=0x20A0,
            product_id=0x42B2,
            name="Test",
            mode=DeviceMode.FIDO,
        )
        
        assert info.product_id_hex == "0x42B2"
    
    def test_is_picokey_true(self) -> None:
        """Test is_picokey returns True for known device."""
        info = DeviceInfo(
            vendor_id=VendorID.PICOKEYS,
            product_id=ProductID.PICO_FIDO,
            name="Pico FIDO",
            mode=DeviceMode.FIDO,
        )
        
        assert info.is_picokey() is True
    
    def test_is_picokey_false(self) -> None:
        """Test is_picokey returns False for unknown device."""
        info = DeviceInfo(
            vendor_id=0x1234,
            product_id=0x5678,
            name="Unknown",
            mode=DeviceMode.UNKNOWN,
        )
        
        assert info.is_picokey() is False
    
    def test_str_representation(self) -> None:
        """Test string representation."""
        info = DeviceInfo(
            vendor_id=VendorID.PICOKEYS,
            product_id=ProductID.PICO_FIDO,
            name="Pico FIDO",
            mode=DeviceMode.FIDO,
            serial_number="ABC123",
            firmware_version="1.0.0",
        )
        
        str_repr = str(info)
        assert "Pico FIDO" in str_repr
        assert "fido" in str_repr
        assert "ABC123" in str_repr
        assert "1.0.0" in str_repr
    
    def test_extra_field_default(self) -> None:
        """Test extra field defaults to empty dict."""
        info = DeviceInfo(
            vendor_id=0x1234,
            product_id=0x5678,
            name="Test",
            mode=DeviceMode.UNKNOWN,
        )
        
        assert info.extra == {}


class TestPicoKeyDevice:
    """Tests for PicoKeyDevice class."""
    
    @pytest.fixture
    def device_info(self) -> DeviceInfo:
        """Create a test DeviceInfo."""
        return DeviceInfo(
            vendor_id=VendorID.PICOKEYS,
            product_id=ProductID.PICO_FIDO,
            name="Pico FIDO",
            mode=DeviceMode.FIDO,
            serial_number="TEST123",
            transport_type=TransportType.HID,
            path="/dev/hidraw0",
        )
    
    def test_creation(self, device_info: DeviceInfo) -> None:
        """Test creating a PicoKeyDevice."""
        device = PicoKeyDevice(device_info)
        
        assert device.name == "Pico FIDO"
        assert device.mode == DeviceMode.FIDO
        assert device.vendor_id == VendorID.PICOKEYS
        assert device.product_id == ProductID.PICO_FIDO
        assert device.serial_number == "TEST123"
    
    def test_not_connected_initially(self, device_info: DeviceInfo) -> None:
        """Test device is not connected initially."""
        device = PicoKeyDevice(device_info)
        
        assert device.is_connected is False
    
    def test_get_info(self, device_info: DeviceInfo) -> None:
        """Test getting device info."""
        device = PicoKeyDevice(device_info)
        info = device.get_info()
        
        assert info.name == "Pico FIDO"
        assert info.mode == DeviceMode.FIDO
    
    def test_repr(self, device_info: DeviceInfo) -> None:
        """Test repr representation."""
        device = PicoKeyDevice(device_info)
        
        repr_str = repr(device)
        assert "PicoKeyDevice" in repr_str
        assert "Pico FIDO" in repr_str
        assert "disconnected" in repr_str
    
    def test_str(self, device_info: DeviceInfo) -> None:
        """Test str representation."""
        device = PicoKeyDevice(device_info)
        
        str_repr = str(device)
        assert "Pico FIDO" in str_repr
