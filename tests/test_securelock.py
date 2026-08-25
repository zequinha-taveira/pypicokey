"""
Tests for SecureLock.
"""

import pytest

from pypicokey.constants import DeviceMode
from pypicokey.exceptions import CommunicationError
from pypicokey.modules.openpgp import OpenPGPInfo, OpenPGPModule
from pypicokey.provisioning.securelock import SecureLock
from tests.fake_transport import make_device


@pytest.fixture
def device():
    return make_device(DeviceMode.OPENPGP)


class TestGetStatus:
    def test_locked_when_admin_retries_zero(self, device, monkeypatch):
        monkeypatch.setattr(
            OpenPGPModule,
            "get_info",
            lambda self: OpenPGPInfo(pin_retries=(3, 0, 0)),
        )
        status = SecureLock(device).get_status()
        assert status.is_locked is True
        assert status.attempts_remaining == 0

    def test_unlocked_when_retries_left(self, device, monkeypatch):
        monkeypatch.setattr(
            OpenPGPModule,
            "get_info",
            lambda self: OpenPGPInfo(pin_retries=(3, 0, 3)),
        )
        status = SecureLock(device).get_status()
        assert status.is_locked is False

    def test_fails_closed_on_communication_error(self, device, monkeypatch):
        """Issue 9: comms errors must not report an unlocked device."""
        monkeypatch.setattr(
            OpenPGPModule,
            "get_info",
            lambda self: (_ for _ in ()).throw(CommunicationError("bus dead")),
        )
        with pytest.raises(CommunicationError):
            SecureLock(device).get_status()

    def test_fails_closed_on_unexpected_error(self, device, monkeypatch):
        monkeypatch.setattr(
            OpenPGPModule,
            "get_info",
            lambda self: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        with pytest.raises(CommunicationError):
            SecureLock(device).get_status()

    def test_unknown_mode_fails_closed(self):
        """Non-OpenPGP modes must not report an unlocked device."""
        status = SecureLock(make_device(DeviceMode.FIDO)).get_status()
        assert status.is_locked is True
        assert status.can_unlock is False
        assert status.lock_type == "unknown"


class TestLock:
    def test_lock_not_implemented(self, device):
        with pytest.raises(NotImplementedError):
            SecureLock(device).lock("12345678")


class TestUnlock:
    def test_unlock_openpgp(self, device, monkeypatch):
        monkeypatch.setattr(
            OpenPGPModule, "verify_pin", lambda self, pin, admin=False: True
        )
        assert SecureLock(device).unlock("12345678") is True

    def test_unlock_other_modes_returns_false(self):
        assert SecureLock(make_device(DeviceMode.FIDO)).unlock("x") is False
