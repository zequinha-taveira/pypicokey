"""
Tests for the OpenPGP module.
"""

import pytest

from pypicokey.constants import DeviceMode
from pypicokey.exceptions import CommunicationError
from pypicokey.modules.openpgp import SLOT_KEY_REFS, OpenPGPModule
from tests.fake_transport import make_ccid_device


class TestSlotKeyRefs:
    """Issue 12: single shared key-ref map used by get/generate key."""

    def test_shared_map_values(self):
        assert SLOT_KEY_REFS == {
            "signature": 0xB6,
            "encryption": 0xB8,
            "authentication": 0xA4,
        }

    def test_get_public_key_uses_correct_ref(self):
        def responder(cla, ins, p1, p2, data=None, le=None):
            if ins == 0xA4:
                return (b"", 0x90, 0x00)
            if ins == 0xCA:
                # TLV: tag 86, len 3
                return (b"\x86\x03\x01\x02\x03", 0x90, 0x00)
            return (b"", 0x90, 0x00)

        device = make_ccid_device(DeviceMode.OPENPGP, responder)
        mod = OpenPGPModule(device)
        key = mod.get_public_key("authentication")

        select_apdu = next(
            a for a in device._transport.apdus if a[1] == 0xA4 and a[2] == 0x01
        )
        assert select_apdu[4] == bytes([0xA4])
        assert key == b"\x01\x02\x03"

    def test_generate_key_uses_correct_ref(self):
        def responder(cla, ins, p1, p2, data=None, le=None):
            if ins == 0x47:
                return (b"\x86\x02\xAA\xBB", 0x90, 0x00)
            if ins == 0xCA:
                return (b"", 0x90, 0x00)
            return (b"", 0x90, 0x00)

        device = make_ccid_device(DeviceMode.OPENPGP, responder)
        mod = OpenPGPModule(device)
        key = mod.generate_key("encryption")

        gen_apdu = next(a for a in device._transport.apdus if a[1] == 0x47)
        assert gen_apdu[4] == bytes([0xB8, 0x00])
        assert key == b"\xaa\xbb"

    def test_invalid_slot(self):
        device = make_ccid_device(DeviceMode.OPENPGP)
        mod = OpenPGPModule(device)
        with pytest.raises(ValueError):
            mod.get_public_key("bogus")


class TestSelect:
    """Issue L1: CommunicationError must not be double-wrapped."""

    def test_select_failure_not_double_wrapped(self):
        def responder(cla, ins, p1, p2, data=None, le=None):
            if ins == 0xA4 and p1 == 0x04:
                return (b"", 0x6A, 0x82)
            return (b"", 0x90, 0x00)

        device = make_ccid_device(DeviceMode.OPENPGP, responder)
        mod = OpenPGPModule(device)
        with pytest.raises(CommunicationError) as exc:
            mod.select()
        assert "OpenPGP selection failed" not in str(exc.value)
