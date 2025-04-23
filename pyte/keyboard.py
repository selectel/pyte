from __future__ import annotations
from enum import IntEnum


class KeypadMode(IntEnum):
    """Supported keypad modes"""
    NUMERIC = 0
    """Keypad sends numbers (default)."""
    APPLICATION = 1
    """Keypad sends control sequences."""
