"""
Tests for the FIDO module (CTAP2 plumbing and clientPin protocol).
"""

import pytest
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from fido2 import cbor

from pypicokey.constants import DeviceMode
from pypicokey.exceptions import CommunicationError, DeviceConnectionError
from pypicokey.modules.fido import (
    PIN_SUBCMD_GET_KEY_AGREEMENT,
    PIN_SUBCMD_SET_PIN,
    FIDOModule,
)
from tests.fake_transport import FakeCtapTransport, make_device


@pytest.fixture
def device():
    return make_device(DeviceMode.FIDO, transport=FakeCtapTransport())


@pytest.fixture
def module(device):
    return FIDOModule(device)


class TestFIDOPlumbing:
    """Issue 3: transport plumbing and status byte handling."""

    def test_requires_connected_transport(self):
        from pypicokey.device import DeviceInfo, PicoKeyDevice

        info = DeviceInfo(
            vendor_id=0x20A0, product_id=0x42B2,
            name="Key", mode=DeviceMode.FIDO,
        )
        device = PicoKeyDevice(info)
        with pytest.raises(DeviceConnectionError):
            FIDOModule(device)

    def test_handler_uses_device_transport(self, device):
        mod = FIDOModule(device)
        assert mod._handler._transport is device._transport
        assert mod.get_retries is not None  # handler wired to real send/receive

    def test_get_info_strips_status_byte(self, device):
        info_map = {
            1: ["U2F", "FIDO2"],
            4: {"rk": True, "up": True},
            5: 2048,
            6: [1],
        }
        device._transport.cbor_handler = lambda payload: b"\x00" + cbor.encode(info_map)
        mod = FIDOModule(device)
        info = mod.get_info()
        assert info.versions == ["U2F", "FIDO2"]
        assert info.supports_resident_keys
        assert info.max_msg_size == 2048

    def test_get_info_error_status_raises(self, device):
        device._transport.cbor_handler = lambda payload: b"\x02"
        mod = FIDOModule(device)
        with pytest.raises(CommunicationError):
            mod.get_info()

    def test_get_retries(self, device):
        def handler(payload):
            request = cbor.decode(payload[1:])
            assert request[2] == 0x01
            return b"\x00" + cbor.encode({3: 5})

        device._transport.cbor_handler = handler
        mod = FIDOModule(device)
        assert mod.get_retries() == 5


class TestFIDOReset:
    """Reset must honor the CTAP2 status byte."""

    def test_reset_success(self, device):
        device._transport.cbor_handler = lambda payload: b"\x00"
        mod = FIDOModule(device)
        assert mod.reset() is True

    def test_reset_error_status_raises(self, device):
        device._transport.cbor_handler = lambda payload: b"\x05"
        mod = FIDOModule(device)
        with pytest.raises(CommunicationError) as exc:
            mod.reset()
        assert "authenticatorReset" in str(exc.value)


class TestSetPin:
    """Issue 2: CTAP2 clientPin setPin protocol."""

    def test_set_pin_protocol(self, device):
        test_priv = ec.generate_private_key(ec.SECP256R1())
        received = {}

        def handler(payload):
            request = cbor.decode(payload[1:])
            sub_cmd = request[2]
            if sub_cmd == PIN_SUBCMD_GET_KEY_AGREEMENT:
                nums = test_priv.public_key().public_numbers()
                cose_key = {
                    1: 2,
                    3: -25,
                    -1: 1,
                    -2: nums.x.to_bytes(32, "big"),
                    -3: nums.y.to_bytes(32, "big"),
                }
                return b"\x00" + cbor.encode({1: cose_key})
            if sub_cmd == PIN_SUBCMD_SET_PIN:
                received["request"] = request
                peer_pub = ec.EllipticCurvePublicKey.from_encoded_point(
                    ec.SECP256R1(), b"\x04" + request[3][-2] + request[3][-3]
                )
                shared = test_priv.exchange(ec.ECDH(), peer_pub)
                decryptor = Cipher(algorithms.AES(shared), modes.CBC(b"\x00" * 16)).decryptor()
                padded = decryptor.update(request[5]) + decryptor.finalize()
                received["pin"] = padded.rstrip(b"\x00")
                h = hmac.HMAC(shared, hashes.SHA256())
                h.update(request[5])
                received["pin_auth_valid"] = h.finalize()[:16] == request[4]
                return b"\x00" + cbor.encode({})
            raise AssertionError(f"Unexpected subCommand {sub_cmd}")

        device._transport.cbor_handler = handler
        mod = FIDOModule(device)
        assert mod.set_pin("123456") is True
        assert received["pin"] == b"123456"
        assert received["pin_auth_valid"]
        assert received["request"][2] == PIN_SUBCMD_SET_PIN

    def test_set_pin_too_short(self, module):
        with pytest.raises(ValueError):
            module.set_pin("123")

    def test_set_pin_error_status(self, device):
        device._transport.cbor_handler = lambda payload: b"\x01"
        mod = FIDOModule(device)
        with pytest.raises(CommunicationError):
            mod.set_pin("123456")
