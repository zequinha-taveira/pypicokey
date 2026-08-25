"""
Tests for the OTP module.
"""

import pytest

from pypicokey.constants import DeviceMode
from pypicokey.exceptions import AuthenticationError, CommunicationError
from pypicokey.modules.otp import OTPModule
from tests.fake_transport import make_ccid_device, make_device


@pytest.fixture
def module():
    device = make_device(DeviceMode.OTP)
    transport = device._transport
    transport.send_apdu.return_value = (b"", 0x90, 0x00)
    return OTPModule(device)


class TestConfigureOtp:
    """Issue 6: flags must be finalized before building the payload."""

    def test_payload_with_access_code(self, module):
        transport = module._device._transport
        result = module.configure_otp(
            slot=1,
            public_id="abcdef12",
            private_id=b"\x01" * 6,
            secret_key=b"\x02" * 16,
            access_code=b"\xaa" * 6,
            touch_required=True,
        )

        assert result is True
        args, kwargs = transport.send_apdu.call_args
        cla, ins, p1, p2 = args
        assert (cla, ins, p2) == (0x00, 0x01, 0x00)  # slot 1 -> P2=0

        payload = kwargs["data"]
        expected_flags = 0x01 | 0x80  # touch + access code
        expected = (
            b"abcdef"          # public ID truncated to 6 bytes
            + b"\x01" * 6      # private ID
            + b"\x02" * 16     # AES key
            + bytes([expected_flags])
            + b"\xaa" * 6      # access code last
        )
        assert payload == expected
        assert len(payload) == 35

    def test_payload_without_access_code(self, module):
        transport = module._device._transport
        module.configure_otp(
            slot=2,
            public_id=b"abc123",
            private_id=b"\x03" * 6,
            secret_key=b"\x04" * 16,
            touch_required=False,
        )

        _, kwargs = transport.send_apdu.call_args
        payload = kwargs["data"]
        expected = (
            b"abc123"
            + b"\x03" * 6
            + b"\x04" * 16
            + bytes([0x00])  # no touch, no access code
        )
        assert payload == expected
        assert len(payload) == 29


class TestConfigureHotp:
    def test_configure_hotp_success(self, module):
        assert module.configure_hotp(1, b"k" * 20) is True


class TestGenerateHotp:
    """generate_hotp must use the dedicated HOTP instruction."""

    def test_sends_ins_hotp_with_slot_p1(self, module):
        transport = module._device._transport
        transport.send_apdu.return_value = (b"\x12\x34\x56", 0x90, 0x00)

        code = module.generate_hotp(2)

        assert code == "123456"
        args, kwargs = transport.send_apdu.call_args
        cla, ins, p1, p2 = args
        assert ins == OTPModule.INS_HOTP == 0x30
        assert p1 == 1  # slot 2 -> P1 = slot - 1
        assert kwargs["le"] == 0

    def test_invalid_slot_raises(self, module):
        with pytest.raises(ValueError):
            module.generate_hotp(3)


class TestSelect:
    """Issue 14: select() must propagate failure."""

    def test_select_non_ccid_marks_selected(self, module):
        assert module.select() is True
        assert module._selected is True

    def test_select_ccid_failure_raises(self):
        def responder(cla, ins, p1, p2, data=None, le=None):
            return (b"", 0x6A, 0x82)

        device = make_ccid_device(DeviceMode.OTP, responder)
        module = OTPModule(device)
        with pytest.raises(CommunicationError):
            module.select()

    def test_select_ccid_success(self):
        def ok(cla, ins, p1, p2, data=None, le=None):
            return (b"", 0x90, 0x00)

        device = make_ccid_device(DeviceMode.OTP, ok)
        module = OTPModule(device)
        assert module.select() is True
        assert module._selected is True


class TestHelpers:
    def test_calculate_hotp_rfc4226(self, module):
        secret = b"12345678901234567890"
        assert module.calculate_hotp(secret, 0) == "755224"
        assert module.calculate_hotp(secret, 1) == "287082"

    def test_invalid_slot(self, module):
        with pytest.raises(ValueError):
            module.configure_otp(3, "abcdef", b"\x00" * 6, b"\x00" * 16)

    def test_wipe_slot_requires_auth(self):
        def locked(cla, ins, p1, p2, data=None, le=None):
            if ins == 0x04 and p1 in (0, 1):
                return (b"", 0x69, 0x82)
            return (b"", 0x90, 0x00)

        device = make_ccid_device(DeviceMode.OTP, locked)
        module = OTPModule(device)
        with pytest.raises(AuthenticationError):
            module.wipe_slot(1)


class TestSwapSlots:
    """Issue L1: CommunicationError must not be double-wrapped."""

    def test_swap_failure_not_double_wrapped(self):
        def responder(cla, ins, p1, p2, data=None, le=None):
            if ins == 0x03:
                return (b"", 0x6A, 0x80)
            return (b"", 0x90, 0x00)

        device = make_ccid_device(DeviceMode.OTP, responder)
        module = OTPModule(device)
        with pytest.raises(CommunicationError) as exc:
            module.swap_slots()
        assert "Slot swap error" not in str(exc.value)
