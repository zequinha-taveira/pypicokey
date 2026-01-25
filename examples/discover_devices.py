#!/usr/bin/env python3
"""
Example: Discover PicoKey devices.

This example shows how to use pypicokey to discover all connected
PicoKey devices and display their information.
"""

from pypicokey import PicoKeyManager, DeviceMode


def main() -> None:
    """Discover and list all PicoKey devices."""
    print("=" * 60)
    print("PicoKey Device Discovery")
    print("=" * 60)
    print()
    
    # Create the device manager
    manager = PicoKeyManager()
    
    # Discover all connected devices
    print("Scanning for PicoKey devices...")
    devices = manager.discover()
    
    if not devices:
        print("No PicoKey devices found.")
        print()
        print("Tips:")
        print("  - Make sure your device is connected via USB")
        print("  - Check that the device drivers are installed")
        print("  - Try reconnecting the device")
        return
    
    print(f"Found {len(devices)} device(s):")
    print()
    
    for i, device in enumerate(devices, 1):
        print(f"Device #{i}")
        print("-" * 40)
        print(f"  Name:       {device.name}")
        print(f"  Mode:       {device.mode}")
        print(f"  Vendor ID:  {device.info.vendor_id_hex}")
        print(f"  Product ID: {device.info.product_id_hex}")
        
        if device.serial_number:
            print(f"  Serial:     {device.serial_number}")
        
        if device.info.firmware_version:
            print(f"  Firmware:   {device.info.firmware_version}")
        
        print(f"  Transport:  {device.info.transport_type}")
        print()
    
    # Show device count by mode
    print("Summary by mode:")
    for mode in DeviceMode:
        count = manager.count_devices(mode_filter=mode)
        if count > 0:
            print(f"  {mode}: {count} device(s)")


if __name__ == "__main__":
    main()
