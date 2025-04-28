"""
This module was created by members of github.com/pytest-dev/pytest.

The MIT License (MIT)

Copyright (c) 2004 Holger Krekel and others

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from __future__ import annotations
from unicodedata import category, east_asian_width, normalize
from functools import lru_cache

__all__ = ("wcwidth", "wcswidth")


@lru_cache(4096)
def wcwidth(c: str) -> int:
    """
    Determine how many columns are needed to display a character in a terminal.

    :param c:
        A character to determine required columns for.

    :returns:
        -1 if the character is not printable.
        0, 1 or 2 for other characters.
    """
    o = ord(c)

    # ASCII fast path.
    if 0x20 <= o < 0x07F:
        return 1

    # Some Cf/Zp/Zl characters which should be zero-width.
    if (
        o == 0x0000
        or 0x200B <= o <= 0x200F
        or 0x2028 <= o <= 0x202E
        or 0x2060 <= o <= 0x2063
    ):
        return 0

    cat = category(c)

    # Control characters.
    if cat == "Cc":
        return -1

    # Combining characters with zero width.
    if cat in ("Me", "Mn"):
        return 0

    # Full/Wide east asian characters.
    if east_asian_width(c) in ("F", "W"):
        return 2

    return 1


def wcswidth(s: str) -> int:
    """
    Determine how many columns are needed to display a string in a terminal.

    :param s:
        String to determine required columns for.

    :returns:
        -1 if the string contains non-printable characters.
    """
    width = 0
    for c in normalize("NFC", s):
        wc = wcwidth(c)
        if wc < 0:
            return -1
        width += wc
    return width
