"""
    pyte.modes
    ~~~~~~~~~~

    This module defines terminal mode switches, used by
    :class:`~pyte.screens.Screen`. There're two types of terminal modes:

    * `non-private` which should be set with ``ESC [ N h``, where ``N``
      is an integer, representing mode being set; and
    * `private` which should be set with ``ESC [ ? N h``.

    The latter are shifted 5 times to the right, to be easily
    distinguishable from the former ones; for example `Origin Mode`
    -- :data:`DECOM` is ``192`` not ``6``.

    >>> DECOM
    192

    :copyright: (c) 2011-2012 by Selectel.
    :copyright: (c) 2012-2017 by pyte authors and contributors,
                    see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

#: *Line Feed/New Line Mode*: When enabled, causes a received
#: :data:`~pyte.control.LF`, :data:`pyte.control.FF`, or
#: :data:`~pyte.control.VT` to move the cursor to the first column of
#: the next line.
LNM = 20

#: *Insert/Replace Mode*: When enabled, new display characters move
#: old display characters to the right. Characters moved past the
#: right margin are lost. Otherwise, new display characters replace
#: old display characters at the cursor position.
IRM = 4


# Private modes.
# ..............

#: *Text Cursor Enable Mode*: determines if the text cursor is
#: visible.
DECTCEM = 25 << 5

#: *Screen Mode*: toggles screen-wide reverse-video mode.
DECSCNM = 5 << 5

#: *Origin Mode*: allows cursor addressing relative to a user-defined
#: origin. This mode resets when the terminal is powered up or reset.
#: It does not affect the erase in display (ED) function.
DECOM = 6 << 5

#: *Auto Wrap Mode*: selects where received graphic characters appear
#: when the cursor is at the right margin.
DECAWM = 7 << 5

#: *Column Mode*: selects the number of columns per line (80 or 132)
#: on the screen.
DECCOLM = 3 << 5


# Private modes: xterm extensions.
# ................................

#: *Use Alternate Screen Buffer*: switches to a secondary screen buffer,
#: leaving the primary one saved and intact. Like :data:`ALTBUF_1047` and
#: :data:`ALTBUF_1049` the alternate buffer starts empty and is discarded on
#: exit; unlike :data:`ALTBUF_1049` the cursor is not saved or restored.
ALTBUF_47 = 47 << 5

#: *Use Alternate Screen Buffer*: switches buffers exactly as
#: :data:`ALTBUF_47` does. The xterm documentation distinguishes the two by
#: when they clear, but no reference implementation preserves alternate-screen
#: contents across a round trip, so there is nothing to distinguish.
ALTBUF_1047 = 1047 << 5

#: *Save Cursor*: saves the cursor as ``DECSC`` does on set, and restores
#: it as ``DECRC`` does on reset, without switching buffers.
ALTBUF_1048 = 1048 << 5

#: *Save Cursor and Use Alternate Screen Buffer*: the combination of
#: :data:`ALTBUF_1047` and :data:`ALTBUF_1048` -- saves the cursor, then
#: switches to the alternate buffer and clears it. Leaving switches back and
#: restores the cursor. This is the mode ``terminfo``-based applications use,
#: and the one full-screen programs such as ``vim``, ``less`` and ``htop``
#: emit in practice.
ALTBUF_1049 = 1049 << 5
