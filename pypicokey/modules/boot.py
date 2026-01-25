"""
Boot module for pypicokey.

This module provides bootloader functionality for flashing firmware
on Pico Boot devices.
"""

from typing import Optional, Callable
from dataclasses import dataclass
from pathlib import Path
import logging

from pypicokey.device import PicoKeyDevice
from pypicokey.constants import DeviceMode
from pypicokey.exceptions import UnsupportedModeError, CommunicationError
from pypicokey.transport.msd import MSDTransport

logger = logging.getLogger(__name__)


@dataclass
class BootInfo:
    """Bootloader information."""
    
    bootloader_version: Optional[str] = None
    board_id: Optional[str] = None
    board_revision: Optional[str] = None
    flash_size: int = 0
    family_id: Optional[str] = None
    info_raw: str = ""


class BootModule:
    """Bootloader operations for Pico devices in boot mode."""
    
    def __init__(self, device: PicoKeyDevice) -> None:
        """Initialize Boot module.
        
        Args:
            device: Connected PicoKeyDevice instance.
        """
        if device.mode != DeviceMode.BOOT:
            raise UnsupportedModeError(
                "Boot module requires a device in boot mode",
                current_mode=str(device.mode),
                required_mode=str(DeviceMode.BOOT),
            )
        
        self._device = device
        self._msd = None

    def _ensure_msd(self) -> MSDTransport:
        if self._msd is None:
            # Check if device already has an MSD transport
            if isinstance(self._device._transport, MSDTransport):
                self._msd = self._device._transport
            else:
                # Try to discover it
                mount = MSDTransport.discover_mount_point()
                if not mount:
                    raise CommunicationError("RP2040 BOOTSEL drive not found or not mounted")
                self._msd = MSDTransport(mount)
                self._msd.open()
        return self._msd

    def get_info(self) -> BootInfo:
        """Get bootloader information by reading INFO_UF2.TXT."""
        msd = self._ensure_msd()
        text = msd.get_info_text()
        
        info = BootInfo(info_raw=text)
        
        # Parse basic fields from INFO_UF2.TXT
        # Format: Field: Value
        for line in text.splitlines():
            if ":" in line:
                key, val = [s.strip() for s in line.split(":", 1)]
                if key == "UF2 Bootloader":
                    info.bootloader_version = val
                elif key == "Board-ID":
                    info.board_id = val
                elif key == "Family-ID":
                    info.family_id = val

        return info
    
    def flash_firmware(
        self,
        firmware_path: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        """Flash firmware to the device by copying the UF2 file."""
        msd = self._ensure_msd()
        
        if not firmware_path.exists():
            raise ValueError(f"Firmware file not found: {firmware_path}")
        
        if firmware_path.suffix.lower() != ".uf2":
            raise ValueError(f"Invalid format, expected .uf2: {firmware_path}")
            
        try:
            if progress_callback:
                progress_callback(0, 100) # Start
            
            success = msd.copy_file(firmware_path)
            
            if progress_callback:
                progress_callback(100, 100) # End
                
            return success
        except Exception as e:
            raise CommunicationError(f"Flashing failed: {e}") from e

    def __repr__(self) -> str:
        return f"BootModule({self._device.name})"
