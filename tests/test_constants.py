"""
Tests for the constants module.
"""

import pytest

from pypicokey.constants import (
    VendorID,
    ProductID,
    DeviceMode,
    TransportType,
    InterfaceClass,
    KNOWN_DEVICES,
    CTAPCommand,
    OpenPGPInstruction,
    HSMState,
)


class TestVendorID:
    """Tests for VendorID enum."""
    
    def test_picokeys_vendor_id(self) -> None:
        """Test PicoKeys vendor ID value."""
        assert VendorID.PICOKEYS == 0x20A0
    
    def test_raspberry_pi_vendor_id(self) -> None:
        """Test Raspberry Pi vendor ID value."""
        assert VendorID.RASPBERRY_PI == 0x2E8A
    
    def test_vendor_id_is_int(self) -> None:
        """Test that vendor IDs are integers."""
        assert isinstance(VendorID.PICOKEYS, int)
        assert isinstance(VendorID.RASPBERRY_PI, int)


class TestProductID:
    """Tests for ProductID enum."""
    
    def test_pico_fido_product_id(self) -> None:
        """Test Pico FIDO product ID value."""
        assert ProductID.PICO_FIDO == 0x42B2
    
    def test_pico_hsm_product_id(self) -> None:
        """Test Pico HSM product ID value."""
        assert ProductID.PICO_HSM == 0x42D1
    
    def test_pico_openpgp_product_id(self) -> None:
        """Test Pico OpenPGP product ID value."""
        assert ProductID.PICO_OPENPGP == 0x42C1


class TestDeviceMode:
    """Tests for DeviceMode enum."""
    
    def test_mode_values(self) -> None:
        """Test device mode string values."""
        assert DeviceMode.FIDO.value == "fido"
        assert DeviceMode.OPENPGP.value == "openpgp"
        assert DeviceMode.HSM.value == "hsm"
        assert DeviceMode.BOOT.value == "boot"
        assert DeviceMode.UNKNOWN.value == "unknown"
    
    def test_mode_str(self) -> None:
        """Test device mode __str__ method."""
        assert str(DeviceMode.FIDO) == "fido"
        assert str(DeviceMode.HSM) == "hsm"


class TestTransportType:
    """Tests for TransportType enum."""
    
    def test_transport_values(self) -> None:
        """Test transport type string values."""
        assert TransportType.HID.value == "hid"
        assert TransportType.CCID.value == "ccid"
        assert TransportType.USB.value == "usb"
    
    def test_transport_str(self) -> None:
        """Test transport type __str__ method."""
        assert str(TransportType.HID) == "hid"


class TestKnownDevices:
    """Tests for KNOWN_DEVICES mapping."""
    
    def test_pico_fido_in_known_devices(self) -> None:
        """Test that Pico FIDO is in known devices."""
        key = (VendorID.PICOKEYS, ProductID.PICO_FIDO)
        assert key in KNOWN_DEVICES
        name, mode = KNOWN_DEVICES[key]
        assert name == "Pico FIDO"
        assert mode == DeviceMode.FIDO
    
    def test_pico_hsm_in_known_devices(self) -> None:
        """Test that Pico HSM is in known devices."""
        key = (VendorID.PICOKEYS, ProductID.PICO_HSM)
        assert key in KNOWN_DEVICES
        name, mode = KNOWN_DEVICES[key]
        assert name == "Pico HSM"
        assert mode == DeviceMode.HSM
    
    def test_pico_openpgp_in_known_devices(self) -> None:
        """Test that Pico OpenPGP is in known devices."""
        key = (VendorID.PICOKEYS, ProductID.PICO_OPENPGP)
        assert key in KNOWN_DEVICES
        name, mode = KNOWN_DEVICES[key]
        assert name == "Pico OpenPGP"
        assert mode == DeviceMode.OPENPGP


class TestCTAPCommand:
    """Tests for CTAP command constants."""
    
    def test_get_info_command(self) -> None:
        """Test authenticatorGetInfo command value."""
        assert CTAPCommand.AUTHENTICATOR_GET_INFO == 0x04
    
    def test_reset_command(self) -> None:
        """Test authenticatorReset command value."""
        assert CTAPCommand.AUTHENTICATOR_RESET == 0x07


class TestOpenPGPInstruction:
    """Tests for OpenPGP instruction constants."""
    
    def test_select_instruction(self) -> None:
        """Test SELECT instruction value."""
        assert OpenPGPInstruction.SELECT == 0xA4
    
    def test_verify_instruction(self) -> None:
        """Test VERIFY instruction value."""
        assert OpenPGPInstruction.VERIFY == 0x20


class TestHSMState:
    """Tests for HSM state enum."""
    
    def test_hsm_state_values(self) -> None:
        """Test HSM state string values."""
        assert HSMState.UNINITIALIZED.value == "uninitialized"
        assert HSMState.INITIALIZED.value == "initialized"
        assert HSMState.LOCKED.value == "locked"
        assert HSMState.UNLOCKED.value == "unlocked"
