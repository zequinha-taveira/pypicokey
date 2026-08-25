"""
Tests for OpenPGP APDU helpers and TLV parsing.
"""

import pytest

from pypicokey.exceptions import CommunicationError
from pypicokey.protocol.openpgp_apdu import OpenPGPAPDU, TLVParser


class TestTLVParser:
    def test_parse_empty_buffer(self):
        assert TLVParser.parse(b"") == {}

    def test_parse_single_tlv(self):
        result = TLVParser.parse(b"\x4F\x03\xAA\xBB\xCC")
        assert result[0x4F] == b"\xaa\xbb\xcc"

    def test_parse_multiple_tlvs(self):
        data = b"\x4F\x02\x01\x02\x5E\x01\xFF"
        result = TLVParser.parse(data)
        assert result[0x4F] == b"\x01\x02"
        assert result[0x5E] == b"\xff"

    def test_parse_multibyte_tag(self):
        data = b"\x5F\x52\x02\x11\x22"
        result = TLVParser.parse(data)
        assert result[0x5F52] == b"\x11\x22"

    def test_parse_three_byte_tag(self):
        data = b"\x3F\x81\x02\x01\xAA"
        assert TLVParser.parse(data)[0x3F8102] == b"\xaa"

    def test_tag_continuation_too_long_raises(self):
        with pytest.raises(CommunicationError):
            TLVParser.parse(b"\x3F\xBF\xFF\xFF\xFF\x01\xAA")

    def test_truncated_tag_continuation_raises(self):
        with pytest.raises(CommunicationError):
            TLVParser.parse(b"\x3F\xBF")

    def test_parse_long_form_81(self):
        value = b"\xAB" * 5
        data = b"\x4F\x81\x05" + value
        assert TLVParser.parse(data)[0x4F] == value

    def test_parse_long_form_82(self):
        value = b"\xCD" * 300
        data = b"\x4F\x82\x01\x2C" + value
        assert TLVParser.parse(data)[0x4F] == value

    def test_truncated_multibyte_tag_raises(self):
        with pytest.raises(CommunicationError):
            TLVParser.parse(b"\x5F")

    def test_missing_length_byte_raises(self):
        with pytest.raises(CommunicationError):
            TLVParser.parse(b"\x4F")

    def test_incomplete_81_length_raises(self):
        with pytest.raises(CommunicationError):
            TLVParser.parse(b"\x4F\x81")

    def test_incomplete_82_length_raises(self):
        with pytest.raises(CommunicationError):
            TLVParser.parse(b"\x4F\x82\x01")

    def test_length_overrun_raises(self):
        # Declares 4 bytes of value but only 1 remains
        with pytest.raises(CommunicationError):
            TLVParser.parse(b"\x4F\x04\xAA")

    def test_overrun_after_valid_prefix(self):
        # First TLV is valid; second one overruns
        with pytest.raises(CommunicationError):
            TLVParser.parse(b"\x4F\x01\x00\x5E\x05\xFF")


class TestOpenPGPAPDU:
    def test_select_application(self):
        apdu = OpenPGPAPDU.select_application()
        assert apdu[:5] == bytes.fromhex("00A4040006")
        assert apdu[5:11] == bytes.fromhex("D27600012401")

    def test_verify_pin_user(self):
        apdu = OpenPGPAPDU.verify_pin("123456")
        assert apdu[:4] == b"\x00\x20\x00\x81"
        assert apdu[4] == 6

    def test_verify_pin_admin(self):
        apdu = OpenPGPAPDU.verify_pin("12345678", admin=True)
        assert apdu[:4] == b"\x00\x20\x00\x83"

    def test_get_data(self):
        apdu = OpenPGPAPDU.get_data(0x004F)
        assert apdu[:4] == b"\x00\xca\x00\x4f"
