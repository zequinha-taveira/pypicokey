"""
CCID transport for pypicokey.

This module provides CCID (Chip Card Interface Device) transport for
communicating with smartcard-based devices like OpenPGP and HSM.
"""

from typing import Optional
import logging

from pypicokey.device import BaseTransport
from pypicokey.exceptions import TransportError, CommunicationError

logger = logging.getLogger(__name__)


class CCIDTransport(BaseTransport):
    """CCID transport for smartcard communication.
    
    This transport is used for devices that expose a CCID interface,
    typically OpenPGP and HSM smartcard functionality.
    
    Example:
        >>> transport = CCIDTransport("Pico OpenPGP")
        >>> transport.open()
        >>> response = transport.send_apdu(0x00, 0xA4, 0x04, 0x00, aid)
        >>> transport.close()
    """
    
    def __init__(self, reader_name: str) -> None:
        """Initialize CCID transport.
        
        Args:
            reader_name: Name of the smartcard reader.
        """
        self._reader_name = reader_name
        self._connection: Optional[object] = None
        self._card: Optional[object] = None
        self._is_open = False
        self._last_response: Optional[bytes] = None
        self._last_sw: tuple[int, int] = (0x00, 0x00)
    
    @property
    def is_open(self) -> bool:
        """Check if transport is open."""
        return self._is_open and self._connection is not None
    
    @property
    def reader_name(self) -> str:
        """Get the reader name."""
        return self._reader_name
    
    def open(self) -> None:
        """Open the CCID connection.
        
        Connects to the smartcard in the specified reader.
        
        Raises:
            TransportError: If connection fails.
        """
        if self._is_open:
            return
        
        try:
            from smartcard.System import readers
            
            # Find the matching reader
            all_readers = readers()
            target_reader = None
            
            for reader in all_readers:
                if self._reader_name in str(reader):
                    target_reader = reader
                    break
            
            if target_reader is None:
                raise TransportError(
                    f"Reader not found: {self._reader_name}",
                    transport_type="CCID",
                )
            
            # Connect to the card
            self._connection = target_reader.createConnection()
            self._connection.connect()
            
            self._is_open = True
            logger.debug(f"Opened CCID connection: {self._reader_name}")
            
        except ImportError as e:
            raise TransportError(
                "pyscard library not installed", transport_type="CCID"
            ) from e
        except Exception as e:
            self._is_open = False
            raise TransportError(f"Failed to open CCID device: {e}", transport_type="CCID") from e
    
    def close(self) -> None:
        """Close the CCID connection."""
        if self._connection:
            try:
                self._connection.disconnect()
                logger.debug("Closed CCID connection")
            except Exception as e:
                logger.warning(f"Error closing CCID connection: {e}")
            finally:
                self._connection = None
                self._is_open = False
    
    def send(self, data: bytes) -> None:
        """Send raw data to the smartcard.
        
        Note: For CCID, use send_apdu() for proper APDU formatting.
        This method sends raw bytes as-is.
        
        Args:
            data: Data bytes to send.
            
        Raises:
            TransportError: If not connected.
            CommunicationError: If send fails.
        """
        if not self.is_open or self._connection is None:
            raise TransportError("CCID device not open", transport_type="CCID")
        
        try:
            apdu_list = list(data)
            response, sw1, sw2 = self._connection.transmit(apdu_list)
            
            # Store response for receive()
            self._last_response = bytes(response)
            self._last_sw = (sw1, sw2)
            
            logger.debug(f"Sent {len(data)} bytes via CCID, SW: {sw1:02X}{sw2:02X}")
            
        except Exception as e:
            raise CommunicationError(f"Failed to send CCID data: {e}") from e
    
    def receive(self, timeout: Optional[float] = None) -> bytes:
        """Receive data from the smartcard.
        
        Returns the response from the last send() operation.
        For CCID, send and receive happen in the same transmit call.
        
        Args:
            timeout: Not used for CCID (included for interface compatibility).
            
        Returns:
            Response bytes including status word.
            
        Raises:
            TransportError: If not connected.
            CommunicationError: If no response available.
        """
        if not self.is_open:
            raise TransportError("CCID device not open", transport_type="CCID")
        
        if self._last_response is None:
            raise CommunicationError("No response available")
        
        # Return response with status word appended
        sw1, sw2 = self._last_sw
        return self._last_response + bytes([sw1, sw2])
    
    def send_apdu(
        self,
        cla: int,
        ins: int,
        p1: int,
        p2: int,
        data: Optional[bytes] = None,
        le: Optional[int] = None,
    ) -> tuple[bytes, int, int]:
        """Send an APDU command to the smartcard.
        
        Constructs and sends an APDU (Application Protocol Data Unit)
        command to the smartcard.
        
        Args:
            cla: Class byte (e.g., 0x00).
            ins: Instruction byte.
            p1: Parameter 1.
            p2: Parameter 2.
            data: Optional command data.
            le: Optional expected response length.
            
        Returns:
            Tuple of (response_data, sw1, sw2).
            
        Raises:
            TransportError: If not connected.
            CommunicationError: If transmission fails.
        """
        if not self.is_open or self._connection is None:
            raise TransportError("CCID device not open", transport_type="CCID")

        try:
            # Build APDU
            apdu = [cla, ins, p1, p2]

            if data:
                apdu.append(len(data))
                apdu.extend(data)

            if le is not None:
                apdu.append(le)
            elif not data:
                # No data and no Le - add Le=0 for response
                apdu.append(0x00)

            logger.debug(f"Sending APDU: {bytes(apdu).hex()}")

            # Case-3 APDUs (data present, no Le) have no trailing Le byte:
            # the last byte belongs to the data field.
            had_le = le is not None or not data

            response, sw1, sw2 = self._connection.transmit(apdu)

            # Handle T=0 status word chaining:
            # 6Cxx: wrong Le, resend with correct Le
            while sw1 == 0x6C:
                logger.debug(f"Resending APDU with Le={sw2:02X} (SW 6C{sw2:02X})")
                if had_le:
                    apdu[-1] = sw2
                else:
                    apdu.append(sw2)
                    had_le = True
                response, sw1, sw2 = self._connection.transmit(apdu)

            # 61xx: more data available, fetch with GET RESPONSE.
            # In T=0 an Le byte of 0x00 means "256 bytes", so the raw sw2
            # value must be masked to a single byte.
            while sw1 == 0x61:
                expected = sw2 & 0xFF
                logger.debug(f"GET RESPONSE for {(expected or 256)} remaining bytes")
                get_resp = [0x00, 0xC0, 0x00, 0x00, expected]
                more, sw1, sw2 = self._connection.transmit(get_resp)
                response = response + more

            logger.debug(f"APDU response: {bytes(response).hex()} SW:{sw1:02X}{sw2:02X}")

            return bytes(response), sw1, sw2

        except Exception as e:
            raise CommunicationError(f"APDU transmission failed: {e}") from e

    def select_application(self, aid: bytes) -> tuple[bytes, int, int]:
        """Select an application by its AID.
        
        Sends a SELECT command to switch to the specified application.
        
        Args:
            aid: Application Identifier bytes.
            
        Returns:
            Tuple of (response_data, sw1, sw2).
        """
        return self.send_apdu(0x00, 0xA4, 0x04, 0x00, aid)
    
    def detect_active_application(self) -> str:
        """Detect which known application is active on the card.
        
        Tries to select known AIDs and returns the name of the first successful one.
        
        Returns:
            Application name ("openpgp", "piv", "fido", "oath", or "unknown").
        """
        apps = {
            "openpgp": AID.OPENPGP,
            "fido": AID.FIDO,
            "piv": AID.PIV,
            "oath": AID.OATH,
        }
        
        for name, aid in apps.items():
            try:
                _, sw1, sw2 = self.select_application(aid)
                if sw1 == 0x90 and sw2 == 0x00:
                    return name
            except Exception:
                continue
        
        return "unknown"
    
    def get_response(self, length: int = 0) -> tuple[bytes, int, int]:
        """Get remaining response data.
        
        Used after receiving SW 61xx (more data available).
        
        Args:
            length: Number of bytes to retrieve.
            
        Returns:
            Tuple of (response_data, sw1, sw2).
        """
        return self.send_apdu(0x00, 0xC0, 0x00, 0x00, le=length)
    
    def __repr__(self) -> str:
        """Return string representation."""
        status = "open" if self._is_open else "closed"
        return f"CCIDTransport({self._reader_name}, {status})"


# Common AIDs
class AID:
    """Common Application Identifiers."""
    
    # OpenPGP application
    OPENPGP = bytes.fromhex("D27600012401")
    
    # PIV application
    PIV = bytes.fromhex("A000000308")
    
    # FIDO application
    FIDO = bytes.fromhex("A0000006472F0001")
    
    # OATH application
    OATH = bytes.fromhex("A0000005272001")
