"""
ATR (Answer To Reset) parser for smartcard identification.

This module provides parsing of ATR bytes returned by smartcards
to identify card type and capabilities.
"""

from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ATRInfo:
    """Parsed ATR information.
    
    Attributes:
        raw: Raw ATR bytes.
        t0: Format byte T0.
        historical_bytes: Historical bytes from ATR.
        tck: Check byte (if present).
        protocols: Supported protocols (T=0, T=1).
        card_type: Detected card type string.
    """
    
    raw: bytes
    t0: int = 0
    historical_bytes: bytes = b""
    tck: Optional[int] = None
    protocols: Optional[list[int]] = None
    card_type: str = "unknown"
    
    def __post_init__(self) -> None:
        if self.protocols is None:
            self.protocols = []
    
    @property
    def supports_t0(self) -> bool:
        """Check if T=0 protocol is supported."""
        return 0 in self.protocols
    
    @property
    def supports_t1(self) -> bool:
        """Check if T=1 protocol is supported."""
        return 1 in self.protocols
    
    def __str__(self) -> str:
        """Return human-readable string."""
        protocols = ", ".join(f"T={p}" for p in self.protocols) or "none"
        return f"ATR({self.raw.hex()}, type={self.card_type}, protocols={protocols})"


class ATRParser:
    """Parser for smartcard ATR (Answer To Reset) bytes.
    
    Parses ATR according to ISO/IEC 7816-3 and identifies
    card type based on historical bytes patterns.
    
    Example:
        >>> parser = ATRParser()
        >>> atr = bytes.fromhex("3B...")
        >>> info = parser.parse(atr)
        >>> print(f"Card type: {info.card_type}")
    """
    
    # Known ATR patterns for PicoKey devices
    KNOWN_PATTERNS = {
        # Pico OpenPGP patterns
        b"OpenPGP": "openpgp",
        b"PicoOpenPGP": "openpgp",
        # Pico HSM patterns
        b"HSM": "hsm",
        b"PicoHSM": "hsm",
        b"SmartCard-HSM": "hsm",
        # FIDO patterns (unlikely in CCID but possible)
        b"FIDO": "fido",
    }
    
    def parse(self, atr: bytes) -> ATRInfo:
        """Parse ATR bytes and extract information.
        
        Args:
            atr: Raw ATR bytes from card.
            
        Returns:
            ATRInfo with parsed information.
        """
        if not atr or len(atr) < 2:
            return ATRInfo(raw=atr or b"", card_type="invalid")
        
        # TS byte (initial character)
        ts = atr[0]
        if ts not in (0x3B, 0x3F):
            logger.warning(f"Invalid TS byte: {ts:02X}")
            return ATRInfo(raw=atr, card_type="invalid")
        
        # T0 byte (format byte)
        t0 = atr[1]
        
        # Parse interface bytes and get historical bytes
        historical_bytes, protocols, tck = self._parse_interface_bytes(atr)
        
        # Detect card type from historical bytes
        card_type = self._detect_card_type(historical_bytes)
        
        return ATRInfo(
            raw=atr,
            t0=t0,
            historical_bytes=historical_bytes,
            tck=tck,
            protocols=protocols,
            card_type=card_type,
        )
    
    def _parse_interface_bytes(
        self, atr: bytes
    ) -> tuple[bytes, list[int], Optional[int]]:
        """Parse interface bytes from ATR.
        
        Returns:
            Tuple of (historical_bytes, protocols, tck).
        """
        t0 = atr[1]
        
        # Number of historical bytes (lower nibble of T0)
        k = t0 & 0x0F
        
        # Interface bytes are indicated by upper nibble of T0
        # and subsequent TD bytes
        protocols = []
        idx = 2
        td = t0
        
        while True:
            # TA, TB, TC present?
            if td & 0x10:  # TA present
                if idx < len(atr):
                    idx += 1
            if td & 0x20:  # TB present
                if idx < len(atr):
                    idx += 1
            if td & 0x40:  # TC present
                if idx < len(atr):
                    idx += 1
            
            # TD present? (indicates next set of interface bytes)
            if td & 0x80:
                if idx < len(atr):
                    td = atr[idx]
                    protocol = td & 0x0F
                    if protocol not in protocols:
                        protocols.append(protocol)
                    idx += 1
                else:
                    break
            else:
                break
        
        # If no TD, assume T=0
        if not protocols:
            protocols = [0]
        
        # Historical bytes (partial slice if the ATR is truncated)
        hist_start = idx
        hist_end = hist_start + k
        historical_bytes = atr[hist_start:min(hist_end, len(atr))]
        
        # TCK (check byte) present if T != 0 only
        tck = None
        if 0 not in protocols or len(protocols) > 1:
            if hist_end < len(atr):
                tck = atr[hist_end]
        
        return historical_bytes, protocols, tck
    
    def _detect_card_type(self, historical_bytes: bytes) -> str:
        """Detect card type from historical bytes.
        
        Args:
            historical_bytes: Historical bytes from ATR.
            
        Returns:
            Card type string.
        """
        if not historical_bytes:
            return "unknown"
        
        # Check known patterns
        for pattern, card_type in self.KNOWN_PATTERNS.items():
            if pattern in historical_bytes:
                return card_type
        
        # Try to decode as ASCII for hints
        try:
            text = historical_bytes.decode("ascii", errors="ignore")
            text_lower = text.lower()
            
            if "openpgp" in text_lower or "pgp" in text_lower:
                return "openpgp"
            elif "hsm" in text_lower:
                return "hsm"
            elif "fido" in text_lower:
                return "fido"
        except Exception:
            pass
        
        return "unknown"
    
    def is_picokey(self, atr: bytes) -> bool:
        """Check if ATR indicates a PicoKey device.
        
        Args:
            atr: Raw ATR bytes.
            
        Returns:
            True if this appears to be a PicoKey device.
        """
        info = self.parse(atr)
        
        # Check historical bytes for PicoKey indicators
        try:
            hist_text = info.historical_bytes.decode("ascii", errors="ignore").lower()
            return "pico" in hist_text or info.card_type in ("openpgp", "hsm")
        except Exception:
            return False
