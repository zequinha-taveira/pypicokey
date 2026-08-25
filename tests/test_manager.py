"""
Tests for the manager module.
"""

import sys
from types import SimpleNamespace

import pytest

from pypicokey.constants import DeviceMode, ProductID, TransportType, VendorID
from pypicokey.device import DeviceInfo, PicoKeyDevice
from pypicokey.exceptions import DeviceNotFoundError
from pypicokey.manager import PicoKeyManager


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


class TestUsbScanBootClassification:
    """RP2040 BOOTSEL devices expose an unknown PID; they must be BOOT."""

    @staticmethod
    def _fake_usb_module(monkeypatch, rasperry_pi_devices):
        import types

        def find(find_all=False, idVendor=None):
            if idVendor == VendorID.RASPBERRY_PI:
                return iter(rasperry_pi_devices)
            return iter([])

        usb_mod = types.ModuleType("usb")
        usb_mod.core = types.SimpleNamespace(find=find)
        monkeypatch.setitem(sys.modules, "usb", usb_mod)
        monkeypatch.setitem(sys.modules, "usb.core", usb_mod.core)

    def test_unknown_raspberry_pi_pid_classified_as_boot(self, monkeypatch):
        dev = SimpleNamespace(
            idProduct=0x0003, serial_number="BOOT123", bus=1, address=5
        )
        self._fake_usb_module(monkeypatch, [dev])

        manager = PicoKeyManager()
        devices = manager._scan_usb_devices()

        assert len(devices) == 1
        assert devices[0].mode == DeviceMode.BOOT
        assert devices[0].serial_number == "BOOT123"

    def test_discover_boot_filter_finds_rp2040_bootsel(self, monkeypatch):
        dev = SimpleNamespace(idProduct=0xDEAD, serial_number=None, bus=1, address=6)
        self._fake_usb_module(monkeypatch, [dev])

        manager = PicoKeyManager()
        monkeypatch.setattr(manager, "_scan_hid_devices", lambda: [])
        monkeypatch.setattr(manager, "_scan_ccid_devices", lambda: [])

        boot_devices = manager.discover(mode_filter=DeviceMode.BOOT)
        assert len(boot_devices) == 1
        assert boot_devices[0].mode == DeviceMode.BOOT


class TestDeduplication:
    @staticmethod
    def make_device(path: str | None, serial: str | None = None):
        info = DeviceInfo(
            vendor_id=VendorID.PICOKEYS,
            product_id=ProductID.PICO_HSM,
            name="Pico HSM",
            mode=DeviceMode.HSM,
            serial_number=serial,
            transport_type=TransportType.CCID,
            path=path,
        )
        return PicoKeyDevice(info)

    def test_two_ccid_readers_same_serial_none_distinct_paths_kept(self):
        manager = PicoKeyManager()
        devices = [
            self.make_device("reader://alpha"),
            self.make_device("reader://beta"),
        ]
        unique = manager._deduplicate_devices(devices)
        assert len(unique) == 2

    def test_same_path_still_deduplicated(self):
        manager = PicoKeyManager()
        devices = [
            self.make_device("reader://alpha"),
            self.make_device("reader://alpha"),
        ]
        unique = manager._deduplicate_devices(devices)
        assert len(unique) == 1
