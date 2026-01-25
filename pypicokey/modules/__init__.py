"""
Modules package for pypicokey.

This package provides feature-specific modules for interacting
with different PicoKey device capabilities.
"""

from pypicokey.modules.fido import FIDOModule
from pypicokey.modules.openpgp import OpenPGPModule
from pypicokey.modules.hsm import HSMModule
from pypicokey.modules.boot import BootModule

__all__ = [
    "FIDOModule",
    "OpenPGPModule",
    "HSMModule",
    "BootModule",
]
