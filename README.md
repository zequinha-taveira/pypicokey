# 🔐 pypicokey

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Alpha-orange)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

**Open-source Python library for managing PicoKey devices**

[Installation](#-installation) •
[CLI Usage](#-cli-usage) •
[Quick Start](#-quick-start) •
[Features](#-features) •
[Documentation](#-documentation) •
[Contributing](#-contributing)

</div>

---

## 📖 Overview

**pypicokey** is a community-driven, open-source Python library for managing PicoKey devices including:

- **Pico FIDO** - FIDO2/WebAuthn security keys
- **Pico OpenPGP** - OpenPGP smartcard functionality
- **Pico HSM** - Hardware Security Module features
- **Pico Boot** - Device bootloader/flashing

### 🎯 Why pypicokey?

This project was created to **restore community alternatives** and preserve open, auditable technical knowledge for PicoKey device management. Key goals:

- ✅ **Free alternative** to proprietary tools
- ✅ **Reusable backend** for GUI (Qt/Tauri) and CLI applications
- ✅ **Modular and testable** architecture
- ✅ **No proprietary license dependencies**
- ✅ **Community-maintained** and transparent

---

## 🚀 Installation

### From PyPI (when available)

```bash
pip install pypicokey
```

### From Source

```bash
git clone https://github.com/picokey-community/pypicokey.git
cd pypicokey
pip install -e .
```

### With Optional Dependencies

```bash
# FIDO2 support
pip install pypicokey[fido]

# Cryptography support
pip install pypicokey[crypto]

# Development tools
pip install pypicokey[dev]

# All optional dependencies
pip install pypicokey[all]
```

---

## 💻 CLI Usage

The library includes a command-line tool named `picokey` for easy device management.

### List Devices
```bash
picokey list
```

### Show Device Details
```bash
picokey info --index 1
```

### Provision a New Device
```bash
picokey provision --index 1 --label "Production Key"
```

---

## ⚡ Quick Start

### Detect Connected Devices

```python
from pypicokey import PicoKeyManager

# Create manager and scan for devices
manager = PicoKeyManager()
devices = manager.discover()

# List all connected PicoKey devices
for device in devices:
    print(f"Found: {device.name} ({device.mode})")
    print(f"  Vendor ID: {hex(device.vendor_id)}")
    print(f"  Product ID: {hex(device.product_id)}")
    print(f"  Serial: {device.serial_number}")
```

### Get Device Information

```python
from pypicokey import PicoKeyManager

manager = PicoKeyManager()
devices = manager.discover()

if devices:
    device = devices[0]
    info = device.get_info()
    print(f"Firmware: {info.firmware_version}")
    print(f"Mode: {info.mode}")
```

---

## ✨ Features

### Current (v0.1.0)

| Feature | Status |
|---------|--------|
| USB device detection (HID Usage Page filtering) | ✅ Implemented |
| Mode identification (ATR & AID selection) | ✅ Implemented |
| FIDO2 CTAP2 Command Support | ✅ Implemented |
| OpenPGP Smartcard Interaction | ✅ Implemented |
| HSM Initialization & Management | ✅ Implemented |
| Secure Provisioning & Locking | ✅ Implemented |
| Rich CLI Interface | ✅ Implemented |
| Stable Python API | ✅ Implemented |

### Planned (Future)

| Feature | Status |
|---------|--------|
| PicoBoot support (boot/flash mode) | 🔄 Planned |
| Extended HSM PKCS#11 mapping | 🔄 Planned |

---

## 🏗️ Architecture

```
┌─────────────────────────────┐
│   Applications (GUI/CLI)    │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│         pypicokey           │
│  ┌───────┬───────┬───────┐  │
│  │ FIDO  │OpenPGP│  HSM  │  │
│  └───┬───┴───┬───┴───┬───┘  │
│      │       │       │      │
│  ┌───┴───────┴───────┴───┐  │
│  │      Transport        │  │
│  │   (USB/HID/CCID)      │  │
│  └───────────────────────┘  │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│      PicoKey Device         │
└─────────────────────────────┘
```

---

## 📂 Project Structure

```
pypicokey/
├── pypicokey/
│   ├── __init__.py          # Public API exports
│   ├── manager.py           # Device discovery & management
│   ├── device.py            # Device abstraction
│   ├── constants.py         # VID/PID, enums, constants
│   ├── exceptions.py        # Custom exceptions
│   ├── transport/           # Low-level communication
│   │   ├── usb.py           # USB transport
│   │   ├── hid.py           # HID transport
│   │   └── ccid.py          # CCID/smartcard transport
│   ├── protocol/            # Protocol implementation
│   │   ├── ctap.py          # CTAPHID & CTAP2
│   │   └── openpgp_apdu.py  # OpenPGP APDUs & TLV
│   ├── modules/             # Feature-specific modules
│   │   ├── fido.py          # FIDO2/WebAuthn
│   │   ├── openpgp.py       # OpenPGP
│   │   ├── hsm.py           # HSM
│   │   └── boot.py          # Bootloader
│   ├── provisioning/        # Device provisioning
│   │   ├── init.py          # Initialization
│   │   └── securelock.py    # Security features
│   ├── utils/               # Utilities
│   │   └── atr.py           # ATR Parser
│   └── cli/                 # Command-line interface
│       └── __main__.py      # App entry point
├── examples/                # Usage examples
├── tests/                   # Unit tests
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## 📚 Documentation

Full documentation coming soon. In the meantime:

- See [examples/](examples/) for usage examples
- Check the source code docstrings
- Open an issue for questions

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone the repository
git clone https://github.com/picokey-community/pypicokey.git
cd pypicokey

# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black pypicokey tests
ruff check pypicokey tests
```

---

## ⚠️ Disclaimer

This is a community project **not affiliated** with the original PicoKey developers. It implements documented protocols only and does not copy any proprietary code.

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- PicoKey firmware documentation
- The open-source security community
- Contributors and testers

---

<div align="center">

**Made with ❤️ by the PicoKey Community**

</div>
