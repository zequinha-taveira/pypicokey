"""
Tests for the BootModule firmware validation errors.
"""

from pathlib import Path

import pytest

from pypicokey.constants import DeviceMode
from pypicokey.exceptions import ProvisioningError
from pypicokey.modules.boot import BootModule
from tests.fake_transport import make_device


def make_boot_module():
    device = make_device(DeviceMode.BOOT)
    module = BootModule(device)
    module._msd = type("FakeMsd", (), {"copy_file": staticmethod(lambda s: True)})()
    return module


class TestFlashFirmwareValidation:
    def test_missing_firmware_raises_provisioning_error(self, tmp_path):
        module = make_boot_module()

        missing = tmp_path / "missing.uf2"
        with pytest.raises(ProvisioningError) as exc:
            module.flash_firmware(missing)
        assert exc.value.stage == "flash"

    def test_non_uf2_extension_raises_provisioning_error(self, tmp_path):
        module = make_boot_module()

        bad = tmp_path / "firmware.bin"
        bad.write_bytes(b"\x00")
        with pytest.raises(ProvisioningError):
            module.flash_firmware(bad)

    def test_valid_uf2_flashes_via_msd(self, tmp_path):
        copied = []

        device = make_device(DeviceMode.BOOT)
        module = BootModule(device)
        module._msd = type(
            "FakeMsd",
            (),
            {"copy_file": staticmethod(lambda src: copied.append(src) or True)},
        )()

        firmware = tmp_path / "fw.uf2"
        firmware.write_bytes(b"UF2\n")

        assert module.flash_firmware(firmware) is True
        assert copied == [Path(firmware)]
