"""
    pyte
    ~~~~

    `pyte` implements a mix of VT100, VT220 and VT520 specification,
    and aims to support most of the `TERM=linux` functionality.

    Two classes: :class:`~pyte.streams.Stream`, which parses the
    command stream and dispatches events for commands, and
    :class:`~pyte.screens.Screen` which, when used with a stream
    maintains a buffer of strings representing the screen of a
    terminal.

    .. warning:: From ``xterm/main.c`` "If you think you know what all
                 of this code is doing, you are probably very mistaken.
                 There be serious and nasty dragons here" -- nothing
                 has changed.

    :copyright: (c) 2011-2012 by Selectel.
    :copyright: (c) 2012-2017 by pyte authors and contributors,
                    see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""
__version__ = "0.8.3.dev"

__all__ = ("KeypadMode",
           "Screen", "DiffScreen", "HistoryScreen", "DebugScreen",
           "Stream", "ByteStream")

from .keyboard import KeypadMode
from .screens import Screen, DiffScreen, HistoryScreen, DebugScreen
from .streams import Stream, ByteStream


if __debug__:
    import io

    def dis(chars: bytes | str) -> None:
        """A :func:`dis.dis` for terminals.

        >>> dis(b"\x07")       # doctest: +NORMALIZE_WHITESPACE
        ["bell", [], {}]
        >>> dis(b"\x1b[20m")   # doctest: +NORMALIZE_WHITESPACE
        ["select_graphic_rendition", [20], {}]
        """
        if isinstance(chars, str):
            chars = chars.encode("utf-8")

        with io.StringIO() as buf:
            ByteStream(DebugScreen(to=buf)).feed(chars)
            print(buf.getvalue())
