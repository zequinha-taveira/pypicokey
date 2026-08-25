"""
Import smoke tests: every public module must import without crashing.
"""

import importlib
import pkgutil

EXPLICIT_MODULES = [
    "pypicokey",
    "pypicokey.constants",
    "pypicokey.device",
    "pypicokey.exceptions",
    "pypicokey.manager",
    "pypicokey.modules",
    "pypicokey.modules.boot",
    "pypicokey.modules.fido",
    "pypicokey.modules.hsm",
    "pypicokey.modules.openpgp",
    "pypicokey.modules.otp",
    "pypicokey.protocol.ctap",
    "pypicokey.protocol.openpgp_apdu",
    "pypicokey.provisioning.init",
    "pypicokey.provisioning.securelock",
    "pypicokey.transport.hid",
    "pypicokey.transport.ccid",
    "pypicokey.transport.msd",
    "pypicokey.transport.usb",
    "pypicokey.utils.atr",
    "pypicokey.cli",
    "pypicokey.cli.__main__",
]


def _all_submodules(package_name: str) -> list[str]:
    package = importlib.import_module(package_name)
    found = []
    for info in pkgutil.walk_packages(package.__path__, prefix=f"{package_name}."):
        if "__pycache__" not in info.name:
            found.append(info.name)
    return found


def test_explicit_public_modules_import() -> None:
    for name in EXPLICIT_MODULES:
        assert importlib.import_module(name) is not None, f"Failed to import {name}"


def test_every_package_submodule_imports() -> None:
    """Walk the whole pypicokey package so future modules are covered too."""
    failures = []
    for name in _all_submodules("pypicokey"):
        try:
            importlib.import_module(name)
        except Exception as e:  # pragma: no cover - reported on failure
            failures.append(f"{name}: {e!r}")
    assert not failures, f"Modules failed to import: {failures}"
