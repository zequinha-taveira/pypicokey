"""
Mass Storage Device (MSD) transport for pypicokey.

This module provides functionality for communicating with Pico devices
in BOOTSEL mode via the mass storage interface.
"""

import os
import shutil
import platform
import logging
from typing import Optional, List
from pathlib import Path

from pypicokey.device import BaseTransport
from pypicokey.exceptions import TransportError, CommunicationError

logger = logging.getLogger(__name__)


class MSDTransport(BaseTransport):
    """Transport for USB Mass Storage Devices.
    
    Used primarily for RP2040 BOOTSEL mode to flash UF2 files.
    """
    
    def __init__(self, mount_point: Optional[str] = None) -> None:
        """Initialize MSD transport.
        
        Args:
            mount_point: Optional path to the drive. If None, it must be discovered.
        """
        self._mount_point = mount_point
        self._is_open = False
    
    @property
    def is_open(self) -> bool:
        return self._is_open
    
    @property
    def mount_point(self) -> Optional[str]:
        return self._mount_point

    def open(self) -> None:
        """Verify the mount point exists."""
        if self._mount_point is None:
            self._mount_point = self.discover_mount_point()
            
        if self._mount_point is None:
            raise TransportError("Pico BOOTSEL drive not found", transport_type="MSD")
            
        if not os.path.exists(self._mount_point):
            raise TransportError(f"Mount point does not exist: {self._mount_point}", transport_type="MSD")
            
        self._is_open = True
        logger.debug(f"Opened MSD transport at {self._mount_point}")

    def close(self) -> None:
        self._is_open = False

    def send(self, data: bytes) -> None:
        """Not applicable for MSD in the same way, but could be used to write a file."""
        raise NotImplementedError("Use copy_file for MSD transport")

    def receive(self, timeout: Optional[float] = None) -> bytes:
        raise NotImplementedError("Use read_file for MSD transport")

    def copy_file(self, src_path: Path) -> bool:
        """Copy a file (e.g. UF2) to the MSD root.
        
        Args:
            src_path: Path to the source file.
            
        Returns:
            True if successful.
        """
        if not self.is_open or self._mount_point is None:
            raise TransportError("MSD transport not open", transport_type="MSD")
            
        try:
            dest_path = Path(self._mount_point) / src_path.name
            logger.info(f"Flashing firmware: {src_path} -> {dest_path}")
            shutil.copy2(src_path, dest_path)
            return True
        except Exception as e:
            raise CommunicationError(f"Failed to copy file to MSD: {e}") from e

    def get_info_text(self) -> str:
        """Read INFO_UF2.TXT if present."""
        if not self.is_open or self._mount_point is None:
            raise TransportError("MSD transport not open", transport_type="MSD")
            
        info_path = Path(self._mount_point) / "INFO_UF2.TXT"
        if info_path.exists():
            try:
                return info_path.read_text()
            except Exception:
                return ""
        return ""

    @staticmethod
    def discover_mount_point() -> Optional[str]:
        """Attempt to find the RP2040 BOOTSEL drive."""
        system = platform.system()
        
        if system == "Windows":
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for i in range(26):
                if bitmask & (1 << i):
                    drive = f"{chr(65 + i)}:\\"
                    if MSDTransport._is_pico_drive(drive):
                        return drive
        elif system == "Linux":
            # Check common mount points or /proc/mounts
            mounts = ["/media/" + os.environ.get("USER", ""), "/run/media/" + os.environ.get("USER", ""), "/mnt"]
            for base in mounts:
                if not os.path.exists(base): continue
                for d in os.listdir(base):
                    path = os.path.join(base, d)
                    if MSDTransport._is_pico_drive(path):
                        return path
        elif system == "Darwin": # macOS
            volumes = "/Volumes"
            for d in os.listdir(volumes):
                path = os.path.join(volumes, d)
                if MSDTransport._is_pico_drive(path):
                    return path
                    
        return None

    @staticmethod
    def _is_pico_drive(path: str) -> bool:
        """Check if a path looks like a Pico BOOTSEL drive."""
        try:
            # Check for INDEX.HTM or INFO_UF2.TXT which are hallmarks of RP2 bootstrap
            if os.path.exists(os.path.join(path, "INFO_UF2.TXT")):
                return True
            # Also check volume label if possible, but INFO_UF2.TXT is more reliable
        except Exception:
            pass
        return False
