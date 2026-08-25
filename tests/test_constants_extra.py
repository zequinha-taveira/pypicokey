"""
Additional tests for constants (OTP mode) and exception aliases.
"""

from pypicokey.constants import DeviceMode
from pypicokey.exceptions import ConnectionError, DeviceConnectionError, PicoKeyError


class TestDeviceModeOTP:
    def test_otp_member_exists(self):
        assert DeviceMode.OTP.value == "otp"

    def test_otp_lookup_by_value(self):
        assert DeviceMode("otp") is DeviceMode.OTP

    def test_str(self):
        assert str(DeviceMode.OTP) == "otp"


class TestConnectionErrorAlias:
    def test_alias_identity(self):
        assert ConnectionError is DeviceConnectionError

    def test_inherits_picokey_error(self):
        err = DeviceConnectionError("nope", device_path="/x")
        assert isinstance(err, PicoKeyError)
        assert "/x" in str(err)
