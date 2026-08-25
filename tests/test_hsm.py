"""
Tests for the HSM module.
"""

import pytest

from pypicokey.constants import DeviceMode, HSMState
from pypicokey.exceptions import AuthenticationError, CommunicationError
from pypicokey.modules.hsm import PQ_ALGORITHMS, HSMModule
from tests.fake_transport import make_ccid_device


def _responder_ok(cla, ins, p1, p2, data=None, le=None):
    return (b"", 0x90, 0x00)


@pytest.fixture
def device():
    return make_ccid_device(DeviceMode.HSM, _responder_ok)


@pytest.fixture
def module(device):
    return HSMModule(device)


class TestPQAlgorithms:
    """Issue 1: module must import and PQ specs must be complete."""

    def test_module_imports(self):
        import pypicokey.modules.hsm  # noqa: F401

    def test_all_algorithms_have_sizes(self):
        assert len(PQ_ALGORITHMS) == 7
        for name, spec in PQ_ALGORITHMS.items():
            assert spec.ciphertext_or_signature_size > 0, name
            assert spec.public_key_size > 0, name
            assert spec.private_key_size > 0, name

    def test_kem_and_signature_families(self):
        kems = [s for s in PQ_ALGORITHMS.values() if s.family == "KEM"]
        sigs = [s for s in PQ_ALGORITHMS.values() if s.family == "Signature"]
        assert len(kems) == 3
        assert len(sigs) == 4


class TestHSMInitialize:
    """Issue 2: initialize() lifecycle."""

    def test_initialize_success(self, device):
        mod = HSMModule(device)
        assert mod.initialize("12345678", "1234") is True

        ins_values = [a[1] for a in device._transport.apdus]
        # select (A4), INITIALIZE APPLET (28), CHANGE REFERENCE DATA x2 (24)
        assert ins_values.count(0x28) == 1
        assert ins_values.count(0x24) == 2

        # PW2 (admin) set before PW1 (user)
        p2_values = [a[3] for a in device._transport.apdus if a[1] == 0x24]
        assert p2_values == [0x82, 0x81]

        pin_data = [a[4] for a in device._transport.apdus if a[1] == 0x24]
        assert pin_data == [b"12345678", b"1234"]

    def test_initialize_with_label(self, device):
        mod = HSMModule(device)
        mod.initialize("12345678", "1234", label="MyKey")
        init_apdu = next(a for a in device._transport.apdus if a[1] == 0x28)
        assert init_apdu[4] == b"\x03MyKey"

    def test_initialize_failure_raises(self):
        def responder(cla, ins, p1, p2, data=None, le=None):
            if ins == 0x28:
                return (b"", 0x6A, 0x82)
            return (b"", 0x90, 0x00)

        mod = HSMModule(make_ccid_device(DeviceMode.HSM, responder))
        with pytest.raises(CommunicationError):
            mod.initialize("12345678", "1234")

    def test_initialize_pin_too_short(self, module):
        with pytest.raises(ValueError):
            module.initialize("123", "1234")
        with pytest.raises(ValueError):
            module.initialize("12345678", "12")


class TestHSMModule:
    def test_requires_hsm_mode(self):
        from pypicokey.exceptions import UnsupportedModeError
        from tests.fake_transport import make_device
        device = make_device(DeviceMode.FIDO)
        with pytest.raises(UnsupportedModeError):
            HSMModule(device)


class TestHSMLogin:
    def test_login_success(self, device):
        assert HSMModule(device).login("1234") is True

    def test_login_wrong_pin_raises_with_retries(self):
        def responder(cla, ins, p1, p2, data=None, le=None):
            if ins == 0x20:
                return (b"", 0x63, 0xC2)
            return (b"", 0x90, 0x00)

        mod = HSMModule(make_ccid_device(DeviceMode.HSM, responder))
        with pytest.raises(AuthenticationError) as exc:
            mod.login("wrong")
        assert exc.value.retries_remaining == 2

    def test_login_other_error_raises_communication_error(self):
        def responder(cla, ins, p1, p2, data=None, le=None):
            if ins == 0x20:
                return (b"", 0x6A, 0x80)
            return (b"", 0x90, 0x00)

        mod = HSMModule(make_ccid_device(DeviceMode.HSM, responder))
        with pytest.raises(CommunicationError):
            mod.login("1234")


class TestHSMGetInfo:
    def test_get_info_does_not_fabricate_values(self, device):
        info = HSMModule(device).get_info()
        assert info.state == HSMState.INITIALIZED
        assert info.version is None
        assert info.total_slots is None
        assert info.used_slots is None
