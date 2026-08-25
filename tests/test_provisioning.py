"""
Tests for device provisioning.
"""

import pytest

from pypicokey.constants import DeviceMode
from pypicokey.modules.fido import FIDOInfo, FIDOModule
from pypicokey.modules.hsm import HSMModule
from pypicokey.modules.openpgp import OpenPGPModule
from pypicokey.provisioning.init import (
    DeviceProvisioner,
    ProvisioningConfig,
    ProvisioningResult,
)
from tests.fake_transport import make_device


@pytest.fixture
def fido_device():
    return make_device(DeviceMode.FIDO)


class TestProvisioningConfig:
    def test_validate_ok(self):
        config = ProvisioningConfig()
        assert config.validate() == []

    def test_validate_short_pins(self):
        config = ProvisioningConfig(user_pin="12", admin_pin="1234")
        errors = config.validate()
        assert len(errors) == 2

    def test_defaults(self):
        config = ProvisioningConfig()
        assert config.key_algorithms == {}

    def test_repr_hides_pins(self):
        config = ProvisioningConfig(
            user_pin="998877",
            admin_pin="11223344",
            current_user_pin="556677",
            current_admin_pin="88990011",
        )
        text = repr(config)
        for secret in ("998877", "11223344", "556677", "88990011"):
            assert secret not in text
        assert "device_label" in text

    def test_current_pins_still_usable_after_repr(self):
        config = ProvisioningConfig(
            current_user_pin="111111", current_admin_pin="22222222"
        )
        repr(config)
        assert config.current_user_pin == "111111"
        assert config.current_admin_pin == "22222222"


class TestProvisioningResult:
    def test_defaults(self):
        result = ProvisioningResult(success=True)
        assert result.generated_keys == []
        assert result.errors == []


class TestFIDOProvisioning:
    def test_set_pin_called(self, fido_device, monkeypatch):
        calls = {}
        monkeypatch.setattr(
            FIDOModule,
            "set_pin",
            lambda self, pin: calls.setdefault("pin", pin) or True,
        )
        provisioner = DeviceProvisioner(fido_device)
        result = provisioner.provision(ProvisioningConfig(user_pin="987654"))
        assert result.success
        assert result.device_mode == DeviceMode.FIDO
        assert calls["pin"] == "987654"

    def test_reset_guard_blocks_provisioning(self, fido_device, monkeypatch):
        """A device that forbids reset must not be wiped nor provisioned."""

        class DisallowedInfo(FIDOInfo):
            pass

        monkeypatch.setattr(
            FIDOModule,
            "get_info",
            lambda self: FIDOInfo(versions=["FIDO2"], options={"resetAllowed": False}),
        )
        reset_calls = []
        monkeypatch.setattr(
            FIDOModule, "reset", lambda self: reset_calls.append(1) or True
        )

        provisioner = DeviceProvisioner(fido_device)
        result = provisioner.provision(
            ProvisioningConfig(user_pin="123456", reset_existing=True)
        )

        assert not reset_calls, "Reset must not run when the device disallows it"
        assert not result.success
        assert any("reset" in e.lower() for e in result.errors)

    def test_reset_failure_aborts(self, fido_device, monkeypatch):
        monkeypatch.setattr(
            FIDOModule, "get_info", lambda self: FIDOInfo(versions=["FIDO2"])
        )

        def boom(self):
            raise RuntimeError("transport gone")

        monkeypatch.setattr(FIDOModule, "reset", boom)
        provisioner = DeviceProvisioner(fido_device)
        result = provisioner.provision(
            ProvisioningConfig(reset_existing=True)
        )
        assert not result.success


class TestOpenPGPProvisioning:
    @pytest.fixture(autouse=True)
    def _stub_openpgp_io(self, monkeypatch):
        monkeypatch.setattr(OpenPGPModule, "select", lambda self: True)
        monkeypatch.setattr(OpenPGPModule, "factory_reset", lambda self: True)

    def test_requires_current_pins_without_reset(self):
        """Changing PINs needs old PINs: reset flag or explicit current PINs."""
        device = make_device(DeviceMode.OPENPGP)
        provisioner = DeviceProvisioner(device)
        result = provisioner.provision(ProvisioningConfig())
        assert not result.success
        assert any("PIN" in e for e in result.errors)

    def test_reset_flow_uses_default_old_pins(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            OpenPGPModule,
            "change_pin",
            lambda self, old, new, admin=False: calls.append((old, new)),
        )
        device = make_device(DeviceMode.OPENPGP)
        provisioner = DeviceProvisioner(device)
        result = provisioner.provision(
            ProvisioningConfig(
                reset_existing=True, user_pin="111111", admin_pin="22222222"
            )
        )
        assert result.success
        assert calls == [("123456", "111111"), ("12345678", "22222222")]

    def test_supplied_current_pins_are_used(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            OpenPGPModule,
            "change_pin",
            lambda self, old, new, admin=False: calls.append((old, new)),
        )
        device = make_device(DeviceMode.OPENPGP)
        provisioner = DeviceProvisioner(device)
        result = provisioner.provision(
            ProvisioningConfig(
                current_user_pin="999999",
                current_admin_pin="88888888",
                user_pin="111111",
                admin_pin="22222222",
            )
        )
        assert result.success
        assert calls == [("999999", "111111"), ("88888888", "22222222")]


class TestHSMProvisioning:
    def test_initialize_called(self, monkeypatch):
        calls = {}

        monkeypatch.setattr(HSMModule, "select", lambda self: True)
        monkeypatch.setattr(
            HSMModule,
            "initialize",
            lambda self, admin, user, label=None: calls.update(
                {"admin": admin, "user": user, "label": label}
            )
            or True,
        )

        device = make_device(DeviceMode.HSM)
        provisioner = DeviceProvisioner(device)
        config = ProvisioningConfig(
            user_pin="111111",
            admin_pin="12345678",
            device_label="Lab",
        )
        result = provisioner.provision(config)

        assert result.success
        assert result.device_mode == DeviceMode.HSM
        assert calls == {"admin": "12345678", "user": "111111", "label": "Lab"}

    def test_unsupported_mode_fails_cleanly(self):
        device = make_device(DeviceMode.BOOT)
        provisioner = DeviceProvisioner(device)
        result = provisioner.provision(ProvisioningConfig())
        assert not result.success

    def test_invalid_config_short_circuits(self):
        device = make_device(DeviceMode.FIDO)
        provisioner = DeviceProvisioner(device)
        result = provisioner.provision(ProvisioningConfig(user_pin="1"))
        assert not result.success
