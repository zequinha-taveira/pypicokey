#!/usr/bin/env python3
"""
Example: Get device information.

This example shows how to connect to a PicoKey device and
retrieve detailed information about it.
"""

from pypicokey import PicoKeyManager, DeviceMode
from pypicokey.modules import FIDOModule, OpenPGPModule, HSMModule


def main() -> None:
    """Get detailed information from a PicoKey device."""
    print("=" * 60)
    print("PicoKey Device Information")
    print("=" * 60)
    print()
    
    # Create the device manager
    manager = PicoKeyManager()
    
    # Get the first available device
    device = manager.get_device()
    
    if device is None:
        print("No PicoKey device found. Please connect a device.")
        return
    
    print(f"Found device: {device.name}")
    print(f"Mode: {device.mode}")
    print()
    
    # Connect to the device using context manager
    try:
        with device:
            print("Connected to device.")
            print()
            
            # Get basic info
            info = device.get_info()
            print("Device Information:")
            print("-" * 40)
            print(f"  Vendor ID:       {info.vendor_id_hex}")
            print(f"  Product ID:      {info.product_id_hex}")
            print(f"  Serial Number:   {info.serial_number or 'N/A'}")
            print(f"  Firmware:        {info.firmware_version or 'N/A'}")
            print(f"  Transport:       {info.transport_type}")
            print(f"  Manufacturer:    {info.manufacturer or 'N/A'}")
            print()
            
            # Get mode-specific information
            if device.mode == DeviceMode.FIDO:
                print("FIDO2 Information:")
                print("-" * 40)
                fido = FIDOModule(device)
                fido_info = fido.get_info()
                print(f"  Versions:        {', '.join(fido_info.versions)}")
                print(f"  Extensions:      {', '.join(fido_info.extensions)}")
                print(f"  Resident Keys:   {'Yes' if fido_info.supports_resident_keys else 'No'}")
                print(f"  User Presence:   {'Yes' if fido_info.supports_user_presence else 'No'}")
                print(f"  Client PIN:      {'Yes' if fido_info.supports_client_pin else 'No'}")
            
            elif device.mode == DeviceMode.OPENPGP:
                print("OpenPGP Information:")
                print("-" * 40)
                openpgp = OpenPGPModule(device)
                openpgp_info = openpgp.get_info()
                print(f"  Version:         {openpgp_info.version or 'N/A'}")
                print(f"  Manufacturer:    {openpgp_info.manufacturer or 'N/A'}")
                print(f"  User PIN Tries:  {openpgp_info.user_pin_retries}")
                print(f"  Admin PIN Tries: {openpgp_info.admin_pin_retries}")
                print(f"  Signatures:      {openpgp_info.signature_count}")
            
            elif device.mode == DeviceMode.HSM:
                print("HSM Information:")
                print("-" * 40)
                hsm = HSMModule(device)
                hsm_info = hsm.get_info()
                print(f"  State:           {hsm_info.state}")
                print(f"  Version:         {hsm_info.version or 'N/A'}")
                print(f"  Total Slots:     {hsm_info.total_slots}")
                print(f"  Used Slots:      {hsm_info.used_slots}")
                print(f"  Available:       {hsm_info.available_slots}")
            
            print()
            print("Disconnected from device.")
    
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
