#!/usr/bin/env python3
"""
Example: Get FIDO2 Information.

This example demonstrates how to use the FIDOModule to retrieve information
from a Pico FIDO device.
"""

from pypicokey import PicoKeyManager, DeviceMode
from pypicokey.modules.fido import FIDOModule
import logging

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)

def main() -> None:
    print("=" * 60)
    print("PicoKey FIDO Module Example")
    print("=" * 60)
    
    manager = PicoKeyManager()
    
    # Discovery
    print("\nScanning for FIDO devices...")
    device = manager.get_device(mode=DeviceMode.FIDO)
    
    if not device:
        print("No Pico FIDO device found.")
        return
    
    print(f"Found: {device.name} (Serial: {device.serial_number})")
    
    try:
        # Connect to the device
        with device:
            # Initialize the FIDO module
            fido = FIDOModule(device)
            
            # Get device info via CTAP2
            print("\nReading FIDO2 information...")
            info = fido.get_info()
            
            print("-" * 40)
            print(f"FIDO Versions:     {', '.join(info.versions)}")
            print(f"AAGUID:            {info.aaguid.hex() if info.aaguid else 'None'}")
            print(f"Max Message Size:  {info.max_msg_size} bytes")
            print(f"Firmware Version:  {info.firmware_version or 'Unknown'}")
            
            print("\nOptions:")
            for opt, val in info.options.items():
                print(f"  - {opt}: {'Yes' if val else 'No'}")
            
            # Check PIN retries if possible
            try:
                retries = fido.get_retries()
                print(f"\nPIN Retries remaining: {retries}")
            except Exception as e:
                print(f"\nCould not get PIN retries: {e}")
                
            print("-" * 40)
            
    except Exception as e:
        print(f"\nError interacting with FIDO device: {e}")

if __name__ == "__main__":
    main()
