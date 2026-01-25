"""
Tests for the manager module.
"""

import pytest

from pypicokey.manager import PicoKeyManager
from pypicokey.constants import DeviceMode
from pypicokey.exceptions import DeviceNotFoundError


class TestPicoKeyManager:
    """Tests for PicoKeyManager class."""
    
    def test_creation(self) -> None:
        """Test creating a PicoKeyManager."""
        manager = PicoKeyManager()
        assert manager is not None
    
    def test_repr(self) -> None:
        """Test repr representation."""
        manager = PicoKeyManager()
        repr_str = repr(manager)
        assert "PicoKeyManager" in repr_str
    
    def test_discover_returns_list(self) -> None:
        """Test that discover returns a list."""
        manager = PicoKeyManager()
        devices = manager.discover()
        assert isinstance(devices, list)
    
    def test_discover_with_mode_filter(self) -> None:
        """Test discover with mode filter."""
        manager = PicoKeyManager()
        devices = manager.discover(mode_filter=DeviceMode.FIDO)
        assert isinstance(devices, list)
        # All devices should be FIDO mode (or empty if none found)
        for device in devices:
            assert device.mode == DeviceMode.FIDO
    
    def test_get_device_returns_none_when_not_found(self) -> None:
        """Test get_device returns None when no device found."""
        manager = PicoKeyManager()
        # Use a non-existent serial number
        device = manager.get_device(serial="NONEXISTENT12345")
        assert device is None
    
    def test_get_device_or_raise_raises_when_not_found(self) -> None:
        """Test get_device_or_raise raises DeviceNotFoundError."""
        manager = PicoKeyManager()
        with pytest.raises(DeviceNotFoundError):
            manager.get_device_or_raise(serial="NONEXISTENT12345")
    
    def test_count_devices_returns_int(self) -> None:
        """Test count_devices returns an integer."""
        manager = PicoKeyManager()
        count = manager.count_devices()
        assert isinstance(count, int)
        assert count >= 0
    
    def test_discover_refresh_false(self) -> None:
        """Test discover with refresh=False uses cache."""
        manager = PicoKeyManager()
        # First call populates cache
        devices1 = manager.discover()
        # Second call should use cache
        devices2 = manager.discover(refresh=False)
        # Should return same list (from cache)
        assert len(devices1) == len(devices2)
