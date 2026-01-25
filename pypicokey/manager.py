"""
Device manager for pypicokey.

This module provides the PicoKeyManager class, which handles device
discovery and provides access to connected PicoKey devices.
"""

from typing import Optional
import logging

from pypicokey.device import PicoKeyDevice, DeviceInfo
from pypicokey.constants import (
    DeviceMode,
    TransportType,
    VendorID,
    ProductID,
    KNOWN_DEVICES,
    InterfaceClass,
)
from pypicokey.exceptions import DeviceNotFoundError

logger = logging.getLogger(__name__)


class PicoKeyManager:
    """Manager for discovering and accessing PicoKey devices.
    
    This class provides the primary interface for finding connected
    PicoKey devices and creating device instances for interaction.
    
    Example:
        >>> manager = PicoKeyManager()
        >>> devices = manager.discover()
        >>> for device in devices:
        ...     print(f"Found: {device.name}")
        
        # Get a specific device
        >>> device = manager.get_device(serial="ABC123")
        >>> if device:
        ...     device.connect()
    """
    
    def __init__(self) -> None:
        """Initialize the PicoKeyManager."""
        self._cached_devices: list[PicoKeyDevice] = []
        self._use_cache = False
    
    def discover(
        self,
        mode_filter: Optional[DeviceMode] = None,
        refresh: bool = True,
    ) -> list[PicoKeyDevice]:
        """Discover all connected PicoKey devices.
        
        Scans for connected USB devices and identifies PicoKey devices
        by their vendor/product IDs and interface classes.
        
        Args:
            mode_filter: Optional filter to only return devices in a specific mode.
            refresh: Whether to rescan for devices (True) or use cached results.
            
        Returns:
            List of PicoKeyDevice instances for each found device.
        """
        if not refresh and self._cached_devices:
            devices = self._cached_devices
        else:
            devices = self._scan_devices()
            self._cached_devices = devices
        
        if mode_filter:
            return [d for d in devices if d.mode == mode_filter]
        
        return devices
    
    def get_device(
        self,
        serial: Optional[str] = None,
        mode: Optional[DeviceMode] = None,
        index: int = 0,
    ) -> Optional[PicoKeyDevice]:
        """Get a specific PicoKey device.
        
        Finds a device matching the given criteria. If multiple devices
        match, returns the one at the specified index.
        
        Args:
            serial: Optional serial number to match.
            mode: Optional device mode to match.
            index: Index of device to return if multiple match (default: 0).
            
        Returns:
            PicoKeyDevice if found, None otherwise.
        """
        devices = self.discover(mode_filter=mode)
        
        if serial:
            devices = [d for d in devices if d.serial_number == serial]
        
        if not devices:
            return None
        
        if index >= len(devices):
            return None
        
        return devices[index]
    
    def get_device_or_raise(
        self,
        serial: Optional[str] = None,
        mode: Optional[DeviceMode] = None,
        index: int = 0,
    ) -> PicoKeyDevice:
        """Get a specific PicoKey device or raise an exception.
        
        Same as get_device(), but raises DeviceNotFoundError if no
        matching device is found.
        
        Args:
            serial: Optional serial number to match.
            mode: Optional device mode to match.
            index: Index of device to return if multiple match (default: 0).
            
        Returns:
            PicoKeyDevice instance.
            
        Raises:
            DeviceNotFoundError: If no matching device is found.
        """
        device = self.get_device(serial=serial, mode=mode, index=index)
        
        if device is None:
            msg_parts = ["No PicoKey device found"]
            if mode:
                msg_parts.append(f"with mode {mode}")
            if serial:
                msg_parts.append(f"with serial {serial}")
            
            raise DeviceNotFoundError(" ".join(msg_parts), serial_number=serial)
        
        return device
    
    def count_devices(self, mode_filter: Optional[DeviceMode] = None) -> int:
        """Count connected PicoKey devices.
        
        Args:
            mode_filter: Optional filter to only count devices in a specific mode.
            
        Returns:
            Number of connected devices.
        """
        return len(self.discover(mode_filter=mode_filter, refresh=False))
    
    def _scan_devices(self) -> list[PicoKeyDevice]:
        """Scan for USB devices and identify PicoKeys.
        
        Returns:
            List of discovered PicoKeyDevice instances.
        """
        devices: list[PicoKeyDevice] = []
        
        # Try HID devices first
        try:
            hid_devices = self._scan_hid_devices()
            devices.extend(hid_devices)
        except Exception as e:
            logger.warning(f"HID scan failed: {e}")
        
        # Try CCID/smartcard devices
        try:
            ccid_devices = self._scan_ccid_devices()
            devices.extend(ccid_devices)
        except Exception as e:
            logger.warning(f"CCID scan failed: {e}")
        
        # Try raw USB devices (for bootloader mode)
        try:
            usb_devices = self._scan_usb_devices()
            devices.extend(usb_devices)
        except Exception as e:
            logger.warning(f"USB scan failed: {e}")
        
        # Remove duplicates (device might show up in multiple scans)
        unique_devices = self._deduplicate_devices(devices)
        
        logger.info(f"Found {len(unique_devices)} PicoKey device(s)")
        return unique_devices
    
    def _scan_hid_devices(self) -> list[PicoKeyDevice]:
        """Scan for HID devices (FIDO2/U2F).
        
        Returns:
            List of HID-based PicoKeyDevice instances.
        """
        devices: list[PicoKeyDevice] = []
        
        try:
            import hid
            
            for dev_info in hid.enumerate():
                vid = dev_info.get("vendor_id", 0)
                pid = dev_info.get("product_id", 0)
                
                # Check if this is a known PicoKey device
                if (vid, pid) in KNOWN_DEVICES:
                    name, mode = KNOWN_DEVICES[(vid, pid)]
                    
                    info = DeviceInfo(
                        vendor_id=vid,
                        product_id=pid,
                        name=name,
                        mode=mode,
                        serial_number=dev_info.get("serial_number"),
                        transport_type=TransportType.HID,
                        path=dev_info.get("path", b"").decode("utf-8", errors="ignore"),
                        manufacturer=dev_info.get("manufacturer_string"),
                        product=dev_info.get("product_string"),
                    )
                    
                    devices.append(PicoKeyDevice(info))
                    logger.debug(f"Found HID device: {name} at {info.path}")
        
        except ImportError:
            logger.warning("hidapi not available, skipping HID scan")
        except Exception as e:
            logger.error(f"Error scanning HID devices: {e}")
        
        return devices
    
    def _scan_ccid_devices(self) -> list[PicoKeyDevice]:
        """Scan for CCID/smartcard devices (OpenPGP, HSM).
        
        Returns:
            List of CCID-based PicoKeyDevice instances.
        """
        devices: list[PicoKeyDevice] = []
        
        try:
            from smartcard.System import readers
            from smartcard.Exceptions import CardConnectionException
            
            for reader in readers():
                reader_name = str(reader)
                logger.debug(f"Found reader: {reader_name}")
                
                # Check if this is a PicoKey reader by name
                if "Pico" in reader_name:
                    # Determine mode from reader name
                    if "OpenPGP" in reader_name:
                        mode = DeviceMode.OPENPGP
                        name = "Pico OpenPGP"
                    elif "HSM" in reader_name:
                        mode = DeviceMode.HSM
                        name = "Pico HSM"
                    else:
                        mode = DeviceMode.UNKNOWN
                        name = "Pico Device"
                    
                    info = DeviceInfo(
                        vendor_id=VendorID.PICOKEYS,
                        product_id=ProductID.UNKNOWN,
                        name=name,
                        mode=mode,
                        transport_type=TransportType.CCID,
                        path=reader_name,
                        manufacturer="PicoKeys",
                    )
                    
                    devices.append(PicoKeyDevice(info))
                    logger.debug(f"Found CCID device: {name}")
        
        except ImportError:
            logger.warning("pyscard not available, skipping CCID scan")
        except Exception as e:
            logger.error(f"Error scanning CCID devices: {e}")
        
        return devices
    
    def _scan_usb_devices(self) -> list[PicoKeyDevice]:
        """Scan for raw USB devices (bootloader mode).
        
        Returns:
            List of USB-based PicoKeyDevice instances.
        """
        devices: list[PicoKeyDevice] = []
        
        try:
            import usb.core
            
            # Look for devices with known PicoKey vendor IDs
            for vid in [VendorID.PICOKEYS, VendorID.RASPBERRY_PI]:
                usb_devices = usb.core.find(find_all=True, idVendor=vid)
                
                if usb_devices:
                    for usb_dev in usb_devices:
                        pid = usb_dev.idProduct
                        
                        # Check if this is a known device or bootloader
                        if (vid, pid) in KNOWN_DEVICES:
                            name, mode = KNOWN_DEVICES[(vid, pid)]
                        else:
                            # Unknown product ID, might be in boot mode
                            name = "Pico Device"
                            mode = DeviceMode.UNKNOWN
                        
                        # Try to get serial number
                        try:
                            serial = usb_dev.serial_number
                        except Exception:
                            serial = None
                        
                        info = DeviceInfo(
                            vendor_id=vid,
                            product_id=pid,
                            name=name,
                            mode=mode,
                            serial_number=serial,
                            transport_type=TransportType.USB,
                            path=f"usb:{usb_dev.bus}:{usb_dev.address}",
                        )
                        
                        devices.append(PicoKeyDevice(info))
                        logger.debug(f"Found USB device: {name}")
        
        except ImportError:
            logger.warning("pyusb not available, skipping USB scan")
        except Exception as e:
            logger.error(f"Error scanning USB devices: {e}")
        
        return devices
    
    def _deduplicate_devices(self, devices: list[PicoKeyDevice]) -> list[PicoKeyDevice]:
        """Remove duplicate devices from the list.
        
        A device is considered a duplicate if it has the same vendor ID,
        product ID, and serial number as another device.
        
        Args:
            devices: List of devices that may contain duplicates.
            
        Returns:
            List of unique devices.
        """
        seen: set[tuple[int, int, Optional[str]]] = set()
        unique: list[PicoKeyDevice] = []
        
        for device in devices:
            key = (device.vendor_id, device.product_id, device.serial_number)
            if key not in seen:
                seen.add(key)
                unique.append(device)
        
        return unique
    
    def __repr__(self) -> str:
        """Return string representation."""
        count = len(self._cached_devices)
        return f"PicoKeyManager({count} cached devices)"
