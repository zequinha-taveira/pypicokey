"""
Tests for transport selection in PicoKeyDevice._create_transport.
"""

import pytest

from pypicokey.constants import DeviceMode, ProductID, TransportType, VendorID
from pypicokey.device import DeviceInfo, PicoKeyDevice
from pypicokey.exceptions import UnsupportedModeError
from pypicokey.transport.msd import MSDTransport
from pypicokey.transport.usb import USBTransport


def make_device(transport_type: TransportType) -> PicoKeyDevice:
    info = DeviceInfo(
        vendor_id=VendorID.RASPBERRY_PI,
        product_id=ProductID.PICO_BOOT,
        name="Pico Boot",
        mode=DeviceMode.BOOT,
        transport_type=transport_type,
        path=r"E:\\",
    )
    return PicoKeyDevice(info)


class TestCreateTransport:
    def test_usb_transport_for_boot_devices(self):
        device = make_device(TransportType.USB)
        transport = device._create_transport()
        assert isinstance(transport, USBTransport)
        assert transport._vendor_id == VendorID.RASPBERRY_PI
        assert transport._product_id == ProductID.PICO_BOOT

    def test_msd_transport(self):
        device = make_device(TransportType.MSD)
        transport = device._create_transport()
        assert isinstance(transport, MSDTransport)
        assert transport.mount_point == r"E:\\"

    def test_msd_transport_without_path_discovers_mount(self):
        info = DeviceInfo(
            vendor_id=VendorID.RASPBERRY_PI,
            product_id=ProductID.PICO_BOOT,
            name="Pico Boot",
            mode=DeviceMode.BOOT,
            transport_type=TransportType.MSD,
        )
        device = PicoKeyDevice(info)
        transport = device._create_transport()
        assert isinstance(transport, MSDTransport)
        assert transport.mount_point is None

    def test_unknown_transport_still_rejected(self):
        device = make_device(TransportType.UNKNOWN)
        with pytest.raises(UnsupportedModeError):
            device._create_transport()
