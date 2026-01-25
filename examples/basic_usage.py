#!/usr/bin/env python3
"""
Example: Basic usage of pypicokey.

This example demonstrates the basic usage patterns for the pypicokey library.
"""

from pypicokey import (
    PicoKeyManager,
    PicoKeyDevice,
    DeviceMode,
    PicoKeyError,
    DeviceNotFoundError,
)


def example_discover_devices() -> None:
    """Example: Discover all connected devices."""
    print("Example 1: Discover devices")
    print("-" * 40)
    
    manager = PicoKeyManager()
    devices = manager.discover()
    
    print(f"Found {len(devices)} device(s)")
    for device in devices:
        print(f"  - {device.name} ({device.mode})")
    print()


def example_get_specific_device() -> None:
    """Example: Get a specific device by mode or serial."""
    print("Example 2: Get specific device")
    print("-" * 40)
    
    manager = PicoKeyManager()
    
    # Get first FIDO device
    fido_device = manager.get_device(mode=DeviceMode.FIDO)
    if fido_device:
        print(f"Found FIDO device: {fido_device.name}")
    else:
        print("No FIDO device found")
    
    # Get device by serial number
    specific_device = manager.get_device(serial="ABC123")
    if specific_device:
        print(f"Found device with serial ABC123: {specific_device.name}")
    else:
        print("Device with serial ABC123 not found")
    print()


def example_connect_with_context_manager() -> None:
    """Example: Connect to a device using context manager."""
    print("Example 3: Connect with context manager")
    print("-" * 40)
    
    manager = PicoKeyManager()
    device = manager.get_device()
    
    if device is None:
        print("No device available")
        return
    
    # Context manager ensures proper cleanup
    try:
        with device:
            print(f"Connected to {device.name}")
            print(f"Is connected: {device.is_connected}")
            # Do operations here...
        print(f"Disconnected. Is connected: {device.is_connected}")
    except PicoKeyError as e:
        print(f"Device error: {e}")
    print()


def example_error_handling() -> None:
    """Example: Handle errors properly."""
    print("Example 4: Error handling")
    print("-" * 40)
    
    manager = PicoKeyManager()
    
    try:
        # This will raise if no device found
        device = manager.get_device_or_raise(serial="NONEXISTENT")
        print(f"Found device: {device.name}")
    except DeviceNotFoundError as e:
        print(f"Device not found: {e}")
    except PicoKeyError as e:
        print(f"General error: {e}")
    print()


def main() -> None:
    """Run all examples."""
    print("=" * 60)
    print("pypicokey Basic Usage Examples")
    print("=" * 60)
    print()
    
    example_discover_devices()
    example_get_specific_device()
    example_connect_with_context_manager()
    example_error_handling()
    
    print("=" * 60)
    print("Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
