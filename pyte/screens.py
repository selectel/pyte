"""
    pyte.screens
    ~~~~~~~~~~~~

    This module provides classes for terminal screens, currently
    it contains three screens with different features:

    * :class:`~pyte.screens.Screen` -- base screen implementation,
      which handles all the core escape sequences, recognized by
      :class:`~pyte.streams.Stream`.
    * If you need a screen to keep track of the changed lines
      (which you probably do need) -- use
      :class:`~pyte.screens.DiffScreen`.
    * If you also want a screen to collect history and allow
      pagination -- :class:`pyte.screen.HistoryScreen` is here
      for ya ;)

    .. note:: It would be nice to split those features into mixin
              classes, rather than subclasses, but it's not obvious
              how to do -- feel free to submit a pull request.

    :copyright: (c) 2011-2012 by Selectel.
    :copyright: (c) 2012-2022 by pyte authors and contributors,
                    see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

import collections
import copy
import json
import math
import os
import sys
import unicodedata
import warnings
from collections import deque, namedtuple
from functools import lru_cache
from bisect import bisect_left, bisect_right

from wcwidth import wcwidth

from . import (
    charsets as cs,
    control as ctrl,
    graphics as g,
    modes as mo
)
from .streams import Stream

wcwidth = lru_cache(maxsize=4096)(wcwidth)

#: A container for screen's scroll margins.
Margins = namedtuple("Margins", "top bottom")

#: A container for savepoint, created on :data:`~pyte.escape.DECSC`.
Savepoint = namedtuple("Savepoint", [
    "cursor",
    "g0_charset",
    "g1_charset",
    "charset",
    "origin",
    "wrap"
])

CharStyle = namedtuple("CharStyle", [
    "fg",
    "bg",
    "bold",
    "italics",
    "underscore",
    "strikethrough",
    "reverse",
    "blink",
])

class LineStats(namedtuple("_LineStats", [
    "empty",
    "chars",
    "columns",
    "occupancy",
    "min",
    "max",
    "span",
    ])):
    """
    :class:`~pyte.screens.LineStats` contains some useful statistics
    about a single line in the screen to understand how the terminal program
    draw on it and how :class:`~pyte.screens.Screen` makes use of the line.

    The basic statistic is the character count over the total count
    of columns of the screen. The line is implemented as a sparse
    buffer so space characters are not really stored and this ratio
    reflects how many non-space chars are. The ratio is also known
    as occupancy.

    A ratio close to 0 means that the line is mostly empty
    and it will consume little memory and the screen's algorithms
    will run faster; close to 1 means that it is mostly full and it will
    have the opposite effects.

    For non-empty lines, the second statistic useful is its range.
    The range of a line is the minimum and maximum x coordinates
    where we find a non-space char.
    For a screen of 80 columns, a range of [10 - 20] means that
    the chars up to the x=10 are spaces and the chars after x=20
    are spaces too.
    The length of the range, also known as the span, is calculated.
    The chars/span ratio gives you how densely packed is the range.

    A ratio close to 0 means that the chars are sparse within the range
    so it is too fragmented and the screen's algorithms will have to jump
    between the chars and the gaps having a lower performance.
    A ratio close to 1 means that they are highly packed and the screen
    will have a better performance.

    With the ratios char/columns and chars/span one can understand
    the balance of sparsity, its distribution and how it will impact
    on the memory and execution time.

    .. note::

    This is not part of the stable API so it may change
    between version of pyte.
    """

    def __repr__(self):
        if self.empty:
            return "chars: {0: >3}/{1} ({2:.2f})".format(
                    self.chars, self.columns, self.occupancy,
                    )
        else:
            return "chars: {0: >3}/{1} ({2:.2f}); range: [{3: >3} - {4: >3}], len: {5: >3} ({6:.2f})".format(
                    self.chars, self.columns, self.occupancy,
                    self.min, self.max, self.span, self.chars/self.span
                    )

class BufferStats(namedtuple("_BufferStats", [
    "empty",
    "entries",
    "columns",
    "lines",
    "falses",
    "blanks",
    "occupancy",
    "min",
    "max",
    "span",
    "line_stats",
    ])):
    """
    :class:`~pyte.screens.BufferStats` has some statistics about
    the buffer of the screen, a 2d sparse matrix representation of the screen.

    The sparse implementation means that empty lines are not stored
    in the buffer explicitly.

    The stats count the real lines (aka entries) and the ratio entries
    over total lines that the screen has (aka occupancy).

    A ratio close to 0 means that the buffer is mostly empty
    and it will consume little memory and the screen's algorithms
    will run faster; close to 1 means that it is mostly full and it will
    have the opposite effects.

    The buffer may have entries for empty lines in two forms:

     - falses lines: empty lines that are the same as the buffer's default
       and therefore should not be in the buffer at all
     - empty lines: non-empty lines but full of spaces. It is suspicious
       because a line full of spaces should not have entries within but
       there are legit cases when this is not true: for example when
       the terminal program erase some chars typing space chars with
       a non-default cursor attributes.

    Both counts are part of the stats with their falses/entries
    and blanks/entries ratios.

    For non-empty buffers the minimum and maximum y-coordinates
    are part of the stats. From there, the range and the span (length)
    are calculated as well the entries/span ratio to see how densely
    packed are the lines.
    See :class:`~pyte.screens.LineStats` for more about these stats.

    After the buffer's stats, the stats of each non-empty line in the buffer
    follows. See :class:`~pyte.screens.LineStats` for that.

    .. note::

    This is not part of the stable API so it may change
    between version of pyte.
    """

    def __repr__(self):
        total_chars = sum(stats.chars for _, stats in self.line_stats)
        bstats = "total chars: {0: >3}/{1} ({2:.2f}%)\n".format(
                total_chars, self.columns*self.lines,
                total_chars/(self.columns*self.lines)
                )

        if self.empty:
            return bstats + \
                    "line entries: {0: >3}/{1} ({2:.2f}), falses: {3:> 3} ({4:.2f}), blanks: {5:> 3} ({6:.2f})\n{7}".format(
                    self.entries, self.lines, self.occupancy,
                    self.falses, self.falses/self.entries,
                    self.blanks, self.blanks/self.entries,
                    "\n".join("{0: >3}: {1}".format(x, stats) for x, stats in self.line_stats)
                    )
        else:
            return bstats + \
                    "line entries: {0: >3}/{1} ({2:.2f}), falses: {3:> 3} ({4:.2f}), blanks: {5:> 3} ({6:.2f}); range: [{7: >3} - {8: >3}], len: {9: >3} ({10:.2f})\n{11}".format(
                    self.entries, self.lines, self.occupancy,
                    self.falses, self.falses/self.entries,
                    self.blanks, self.blanks/self.entries,
                    self.min, self.max, self.span, self.entries/self.span,
                    "\n".join("{0: >3}: {1}".format(x, stats) for x, stats in self.line_stats)
                    )


class Char:
    """
    A single styled on-screen character. The character is made
    of an unicode character (data), its width and its style.

    :param str data: unicode character. Invariant: ``len(data) == 1``.
    :param bool width: the width in terms of cells to display this char.
    :param CharStyle style: the style of the character.

    The :meth:`~pyte.screens.Char.from_attributes` allows to create
    a new :class:`~pyte.screens.Char` object
    setting each attribute, one by one, without requiring and explicit
    :class:`~pyte.screens.CharStyle` object.

    The supported attributes are:

    :param str fg: foreground colour. Defaults to ``"default"``.
    :param str bg: background colour. Defaults to ``"default"``.
    :param bool bold: flag for rendering the character using bold font.
                      Defaults to ``False``.
    :param bool italics: flag for rendering the character using italic font.
                         Defaults to ``False``.
    :param bool underscore: flag for rendering the character underlined.
                            Defaults to ``False``.
    :param bool strikethrough: flag for rendering the character with a
                               strike-through line. Defaults to ``False``.
    :param bool reverse: flag for swapping foreground and background colours
                         during rendering. Defaults to ``False``.
    :param bool blink: flag for rendering the character blinked. Defaults to
                       ``False``.

    The attributes data, width and style of :class:`~pyte.screens.Char`
    must be considered read-only. Any modification is undefined.
    If you want to modify a :class:`~pyte.screens.Char`, use the public
    interface of :class:`~pyte.screens.Screen`.
    """
    __slots__ = (
        "data",
        "width",
        "style",
        )

    # List the properties of this Char instance including its style's properties
    # The order of this _fields is maintained for backward compatibility
    _fields = ("data",) + CharStyle._fields + ("width",)

    def __init__(self, data, width, style):
        self.data = data
        self.width = width
        self.style = style

    @classmethod
    def from_attributes(cls, data=" ", fg="default", bg="default", bold=False, italics=False, underscore=False,
                strikethrough=False, reverse=False, blink=False):
        style = CharStyle(fg, bg, bold, italics, underscore, strikethrough, reverse, blink)
        return Char(data, wcwidth(data), style)

    @property
    def fg(self):
        return self.style.fg

    @property
    def bg(self):
        return self.style.bg

    @property
    def bold(self):
        return self.style.bold

    @property
    def italics(self):
        return self.style.italics

    @property
    def underscore(self):
        return self.style.underscore

    @property
    def strikethrough(self):
        return self.style.strikethrough

    @property
    def reverse(self):
        return self.style.reverse

    @property
    def blink(self):
        return self.style.blink

    def copy_and_change(self, **kargs):
        fields = self._asdict()
        fields.update(kargs)
        return Char(**fields)

    def copy(self):
        return Char(self.data, self.width, self.style)

    def as_dict(self):
        return {name: getattr(self, name) for name in self._fields}

    def __eq__(self, other):
        if not isinstance(other, Char):
            raise TypeError()

        return all(getattr(self, name) == getattr(other, name) for name in self._fields)

    def __ne__(self, other):
        if not isinstance(other, Char):
            raise TypeError()

        return any(getattr(self, name) != getattr(other, name) for name in self._fields)

    def __repr__(self):
        r = "'%s'" % self.data
        attrs = []
        if self.fg != "default":
            attrs.append("fg=%s" % self.fg)
        if self.bg != "default":
            attrs.append("bg=%s" % self.bg)

        for attrname in ['bold', 'italics', 'underscore',
                'strikethrough', 'reverse', 'blink']:
            val = getattr(self, attrname)
            if val:
                attrs.append("%s=%s" % (attrname, val))

        if attrs:
            r += " (" + (", ".join(attrs)) + ")"

        return r


class Cursor:
    """Screen cursor.

    :param int x: 0-based horizontal cursor position.
    :param int y: 0-based vertical cursor position.
    :param pyte.screens.Char attrs: cursor attributes (see
        :meth:`~pyte.screens.Screen.select_graphic_rendition`
        for details).
    """
    __slots__ = ("x", "y", "attrs", "hidden")

    def __init__(self, x, y, attrs):
        self.x = x
        self.y = y
        self.attrs = attrs
        self.hidden = False


class Line(dict):
    """A line or row of the screen.

    This dict subclass implements a sparse array for 0-based
    indexed characters that represents a single line or row of the screen.

    :param pyte.screens.Char default: a :class:`~pyte.screens.Char` instance
        to be used as default. See :meth:`~pyte.screens.Line.char_at`
        for details.
    """
    __slots__ = ('default', )
    def __init__(self, default):
        self.default = default

    def write_data(self, x, data, width, style):
        """
        Update the char at the position x with the new data, width and style.
        If no char is at that position, a new char is created and added
        to the line.
        """
        if x in self:
            char = self[x]
            char.data = data
            char.width = width
            char.style = style
        else:
            self[x] = Char(data, width, style)

    def char_at(self, x):
        """
        Return the character at the given position x. If no char exists,
        create a new one and add it to the line before returning it.

        This is a shortcut of `line.setdefault(x, line.default.copy())`
        but avoids the copy if the char already exists.
        """
        try:
            return self[x]
        except KeyError:
            self[x] = char = self.default.copy()
            return char

    def stats(self, screen):
        """
        Return a :class:`~pyte.screens.LineStats` object with the statistics
        of the line.

        .. note::

        This is not part of the stable API so it may change
        between version of pyte.
        """
        return LineStats(
                empty=not bool(self),
                chars=len(self),
                columns=screen.columns,
                occupancy=len(self)/screen.columns,
                min=min(self) if self else None,
                max=max(self) if self else None,
                span=(max(self) - min(self)) if self else None
                )

class Buffer(dict):
    """A 2d matrix representation of the screen.

    This dict subclass implements a sparse array for 0-based
    indexed lines that represents the screen. Each line is then
    a sparse array for the characters in the same row (see
    :class:`~pyte.screens.Line`).

    :param pyte.screens.Screen screen: a :class:`~pyte.screens.Screen` instance
        to be used when a default line needs to be created.
        See :meth:`~pyte.screens.Buffer.line_at` for details.
    """
    __slots__ = ('_screen', )
    def __init__(self, screen):
        self._screen = screen

    def line_at(self, y):
        """
        Return the line at the given position y. If no line exists,
        create a new one and add it to the buffer before returning it.

        This is a shortcut of `buffer.setdefault(y, screen.default_line())`
        but avoids the copy if the line already exists.
        """
        try:
            return self[y]
        except KeyError:
            self[y] = line = self._screen.default_line()
            return line

class LineView:
    """
    A read-only view of an horizontal line of the screen.

    :param pyte.screens.Line line: a :class:`~pyte.screens.Line` instance

    Modifications to the internals of the screen is still possible through
    this :class:`~pyte.screens.LineView` however any modification
    will result in an undefined behaviour. Don't do that.

    See :class:`~pyte.screens.BufferView`.
    """
    __slots__ = ("_line",)
    def __init__(self, line):
        self._line = line

    def __getitem__(self, x):
        try:
            return self._line[x]
        except KeyError:
            return self._line.default

    def __eq__(self, other):
        if not isinstance(other, LineView):
            raise TypeError()

        return self._line == other._line

    def __ne__(self, other):
        if not isinstance(other, LineView):
            raise TypeError()

        return self._line == other._line


class BufferView:
    """
    A read-only view of the screen.

    :param pyte.screens.Screen screen: a :class:`~pyte.screens.Screen` instance

    Modifications to the internals of the screen is still possible through
    this :class:`~pyte.screens.BufferView` however any modification
    will result in an undefined behaviour. Don't do that.

    Any modification to the screen must be done through its methods
    (principally :meth:`~pyte.screens.Screen.draw`).

    This view allows the user to iterate over the lines and chars of
    the buffer to query their attributes.

    As an example:

    view = screen.buffer  # get a BufferView
    for y in view:
        line = view[y]  # get a LineView (do it once per y line)
        for x in line:
            char = line[x]  # get a Char
            print(char.data, char.fg, char.bg)  # access to char's attrs
    """
    __slots__ = ("_buffer", "_screen")
    def __init__(self, screen):
        self._screen = screen
        self._buffer = screen._buffer

    def __getitem__(self, y):
        try:
            line = self._buffer[y]
        except KeyError:
            line = Line(self._screen.default_char)

        return LineView(line)

    def __len__(self):
        return self._screen.lines

class _NullSet(collections.abc.MutableSet):
    """Implementation of a set that it is always empty."""
    def __contains__(self, x):
        return False

    def __iter__(self):
        return iter(set())

    def __len__(self):
        return 0

    def add(self, x):
        return

    def discard(self, x):
        return

    def update(self, it):
        return

class Screen:
    """
    A screen is an in-memory matrix of characters that represents the
    screen display of the terminal. It can be instantiated on its own
    and given explicit commands, or it can be attached to a stream and
    will respond to events.

    :param int columns: count of columns for the screen (width).
    :param int lines: count of lines for the screen (height).

    :param bool track_dirty_lines: track which lines were modified
    (see `dirty` attribute). If it is false do not track any line.
    Defaults to True.

    :param bool disable_display_graphic: disables the modification
    of cursor attributes disabling :meth:`~pyte.screens.Screen.select_graphic_rendition`.
    Defaults to False.

    .. note::

    If you don't need the functionality, setting `track_dirty_lines`
    to False and `disable_display_graphic` to True can
    make :class:`~pyte.screens.Screen` to work faster and consume less
    resources.

    .. attribute:: buffer

       A ``lines x columns`` :class:`~pyte.screens.Char` matrix view of
       the screen. Under the hood :class:`~pyte.screens.Screen` implements
       a sparse matrix but `screen.buffer` returns a dense view.
       See :class:`~pyte.screens.BufferView`

    .. attribute:: dirty

       A set of line numbers, which should be re-drawn. The user is responsible
       for clearing this set when changes have been applied.

       >>> screen = Screen(80, 24)
       >>> screen.dirty.clear()
       >>> screen.draw("!")
       >>> list(screen.dirty)
       [0]

       If `track_dirty_lines` was set to false, this `dirty` set will be
       always empty.

       .. versionadded:: 0.7.0

    .. attribute:: cursor

       Reference to the :class:`~pyte.screens.Cursor` object, holding
       cursor position and attributes.

    .. attribute:: margins

       Margins determine which screen lines move during scrolling
       (see :meth:`index` and :meth:`reverse_index`). Characters added
       outside the scrolling region do not make the screen to scroll.

       The margins are a pair 0-based top and bottom line indices
       set to screen boundaries by default.

    .. attribute:: charset

       Current charset number; can be either ``0`` or ``1`` for `G0`
       and `G1` respectively, note that `G0` is activated by default.

    .. note::

       According to ``ECMA-48`` standard, **lines and columns are
       1-indexed**, so, for instance ``ESC [ 10;10 f`` really means
       -- move cursor to position (9, 9) in the display matrix.

    .. versionchanged:: 0.4.7
    .. warning::

       :data:`~pyte.modes.LNM` is reset by default, to match VT220
       specification. Unfortunately this makes :mod:`pyte` fail
       ``vttest`` for cursor movement.

    .. versionchanged:: 0.4.8
    .. warning::

       If `DECAWM` mode is set than a cursor will be wrapped to the
       **beginning** of the next line, which is the behaviour described
       in ``man console_codes``.

    .. seealso::

       `Standard ECMA-48, Section 6.1.1 \
       <http://ecma-international.org/publications/standards/Ecma-048.htm>`_
       for a description of the presentational component, implemented
       by ``Screen``.
    """
    @property
    def default_char(self):
        """An empty character with default foreground and background colors."""
        style = self._default_style_reversed if mo.DECSCNM in self.mode else self._default_style
        return Char(" ", wcwidth(" "), style)

    def default_line(self):
        return Line(self.default_char)

    def __init__(self, columns, lines, track_dirty_lines=True, disable_display_graphic=False):
        self.savepoints = []
        self.columns = columns
        self.lines = lines
        self._buffer = Buffer(self)
        self.dirty = set() if track_dirty_lines else _NullSet()
        self.disabled_display_graphic = disable_display_graphic

        self._default_style = CharStyle(
                fg="default", bg="default", bold=False,
                italics=False, underscore=False,
                strikethrough=False, reverse=False, blink=False)
        self._default_style_reversed = self._default_style._replace(reverse=True)

        self.reset()

    def __repr__(self):
        return ("{0}({1}, {2})".format(self.__class__.__name__,
                                       self.columns, self.lines))

    @property
    def buffer(self):
        return BufferView(self)

    def stats(self):
        """
        Return the statistcs of the buffer.

        .. note::

        This is not part of the stable API so it may change
        between version of pyte.
        """
        buffer = self._buffer
        return BufferStats(
                empty=not bool(buffer),
                entries=len(buffer),
                columns=self.columns,
                lines=self.lines,
                falses=len([line for line in buffer.values() if not line]),
                blanks=len([line for line in buffer.values() if all(char.data == " " for char in line.values())]),
                occupancy=len(buffer)/self.lines,
                min=min(buffer) if buffer else None,
                max=max(buffer) if buffer else None,
                span=(max(buffer) - min(buffer)) if buffer else None,
                line_stats=[(x, line.stats(self)) for x, line in sorted(buffer.items())]
                )

    @property
    def display(self):
        """A :func:`list` of screen lines as unicode strings."""
        # screen.default_char is always the space character
        # We can skip the lookup of it and set the padding char
        # directly
        padding = " "

        prev_y = -1
        output = []
        columns = self.columns
        for y, line in sorted(self._buffer.items()):
            empty_lines = y - (prev_y + 1)
            if empty_lines:
                output.extend([padding * columns] * empty_lines)
            prev_y = y

            is_wide_char = False
            prev_x = -1
            display_line = []
            for x, cell in sorted(line.items()):
                if x >= columns:
                    break

                gap = x - (prev_x + 1)
                if gap:
                    display_line.append(padding * gap)

                prev_x = x

                if is_wide_char:  # Skip stub
                    is_wide_char = False
                    continue
                char = cell.data
                is_wide_char = cell.width == 2
                display_line.append(char)

            gap = columns - (prev_x + 1)
            if gap:
                display_line.append(padding * gap)

            output.append("".join(display_line))

        empty_lines = self.lines - (prev_y + 1)
        if empty_lines:
            output.extend([padding * columns] * empty_lines)

        return output

    def reset(self):
        """Reset the terminal to its initial state.

        * Scrolling margins are reset to screen boundaries.
        * Cursor is moved to home location -- ``(0, 0)`` and its
          attributes are set to defaults (see :attr:`default_char`).
        * Screen is cleared -- each character is reset to
          :attr:`default_char`.
        * Tabstops are reset to "every eight columns".
        * All lines are marked as :attr:`dirty`.

        .. note::

           Neither VT220 nor VT102 manuals mention that terminal modes
           and tabstops should be reset as well, thanks to
           :manpage:`xterm` -- we now know that.
        """
        self.dirty.update(range(self.lines))
        self._buffer.clear()
        self.margins = Margins(0, self.lines - 1)

        self.mode = set([mo.DECAWM, mo.DECTCEM])

        self.title = ""
        self.icon_name = ""

        self.charset = 0
        self.g0_charset = cs.LAT1_MAP
        self.g1_charset = cs.VT100_MAP

        # From ``man terminfo`` -- "... hardware tabs are initially
        # set every `n` spaces when the terminal is powered up. Since
        # we aim to support VT102 / VT220 and linux -- we use n = 8.
        self.tabstops = set(range(8, self.columns, 8))

        self.cursor = Cursor(0, 0, self.default_char.copy())
        self.cursor_position()

        self.saved_columns = None

    def resize(self, lines=None, columns=None):
        """Resize the screen to the given size.

        If the requested screen size has more lines than the existing
        screen, lines will be added at the bottom. If the requested
        size has less lines than the existing screen lines will be
        clipped at the top of the screen. Similarly, if the existing
        screen has less columns than the requested screen, columns will
        be added at the right, and if it has more -- columns will be
        clipped at the right.

        :param int lines: number of lines in the new screen.
        :param int columns: number of columns in the new screen.

        .. versionchanged:: 0.7.0

           If the requested screen size is identical to the current screen
           size, the method does nothing.
        """
        lines = lines or self.lines
        columns = columns or self.columns

        if lines == self.lines and columns == self.columns:
            return  # No changes.

        self.dirty.update(range(lines))

        if lines < self.lines:
            self.save_cursor()
            self.cursor_position(0, 0)
            self.delete_lines(self.lines - lines)  # Drop from the top.
            self.restore_cursor()

        if columns < self.columns:
            for line in self._buffer.values():
                pop = line.pop
                non_empty_x = sorted(line)
                begin = bisect_left(non_empty_x, columns)

                list(map(pop, non_empty_x[begin:]))

        self.lines, self.columns = lines, columns
        self.set_margins()

    def set_margins(self, top=None, bottom=None):
        """Select top and bottom margins for the scrolling region.

        :param int top: the smallest line number that is scrolled.
        :param int bottom: the biggest line number that is scrolled.
        """
        # XXX 0 corresponds to the CSI with no parameters.
        if (top is None or top == 0) and bottom is None:
            self.margins = Margins(0, self.lines - 1)
            return

        margins = self.margins

        # Arguments are 1-based, while :attr:`margins` are zero
        # based -- so we have to decrement them by one. We also
        # make sure that both of them is bounded by [0, lines - 1].
        if top is None:
            top = margins.top
        else:
            top = max(0, min(top - 1, self.lines - 1))
        if bottom is None:
            bottom = margins.bottom
        else:
            bottom = max(0, min(bottom - 1, self.lines - 1))

        # Even though VT102 and VT220 require DECSTBM to ignore
        # regions of width less than 2, some programs (like aptitude
        # for example) rely on it. Practicality beats purity.
        if bottom - top >= 1:
            self.margins = Margins(top, bottom)

            # The cursor moves to the home position when the top and
            # bottom margins of the scrolling region (DECSTBM) changes.
            self.cursor_position()

    def set_mode(self, *modes, **kwargs):
        """Set (enable) a given list of modes.

        :param list modes: modes to set, where each mode is a constant
                           from :mod:`pyte.modes`.
        """
        # Private mode codes are shifted, to be distinguished from non
        # private ones.
        if kwargs.get("private"):
            modes = [mode << 5 for mode in modes]
            if mo.DECSCNM in modes:
                self.dirty.update(range(self.lines))

        self.mode.update(modes)

        # When DECOLM mode is set, the screen is erased and the cursor
        # moves to the home position.
        if mo.DECCOLM in modes:
            self.saved_columns = self.columns
            self.resize(columns=132)
            self.erase_in_display(2)
            self.cursor_position()

        # According to VT520 manual, DECOM should also home the cursor.
        if mo.DECOM in modes:
            self.cursor_position()

        # Mark all displayed characters as reverse.
        if mo.DECSCNM in modes:
            for line in self._buffer.values():
                line.default.style = line.default.style._replace(reverse=True)
                for char in line.values():
                    char.style = char.style._replace(reverse=True)

            self.select_graphic_rendition(7)  # +reverse.

        # Make the cursor visible.
        if mo.DECTCEM in modes:
            self.cursor.hidden = False

    def reset_mode(self, *modes, **kwargs):
        """Reset (disable) a given list of modes.

        :param list modes: modes to reset -- hopefully, each mode is a
                           constant from :mod:`pyte.modes`.
        """
        # Private mode codes are shifted, to be distinguished from non
        # private ones.
        if kwargs.get("private"):
            modes = [mode << 5 for mode in modes]
            if mo.DECSCNM in modes:
                self.dirty.update(range(self.lines))

        self.mode.difference_update(modes)

        # Lines below follow the logic in :meth:`set_mode`.
        if mo.DECCOLM in modes:
            if self.columns == 132 and self.saved_columns is not None:
                self.resize(columns=self.saved_columns)
                self.saved_columns = None
            self.erase_in_display(2)
            self.cursor_position()

        if mo.DECOM in modes:
            self.cursor_position()

        if mo.DECSCNM in modes:
            for line in self._buffer.values():
                line.default.style = line.default.style._replace(reverse=False)
                for char in line.values():
                    char.style = char.style._replace(reverse=False)

            self.select_graphic_rendition(27)  # -reverse.

        # Hide the cursor.
        if mo.DECTCEM in modes:
            self.cursor.hidden = True

    def define_charset(self, code, mode):
        """Define ``G0`` or ``G1`` charset.

        :param str code: character set code, should be a character
                         from ``"B0UK"``, otherwise ignored.
        :param str mode: if ``"("`` ``G0`` charset is defined, if
                         ``")"`` -- we operate on ``G1``.

        .. warning:: User-defined charsets are currently not supported.
        """
        if code in cs.MAPS:
            if mode == "(":
                self.g0_charset = cs.MAPS[code]
            elif mode == ")":
                self.g1_charset = cs.MAPS[code]

    def shift_in(self):
        """Select ``G0`` character set."""
        self.charset = 0

    def shift_out(self):
        """Select ``G1`` character set."""
        self.charset = 1

    def draw(self, data):
        """Display decoded characters at the current cursor position and
        advances the cursor if :data:`~pyte.modes.DECAWM` is set.

        :param str data: text to display.

        .. versionchanged:: 0.5.0

           Character width is taken into account. Specifically, zero-width
           and unprintable characters do not affect screen state. Full-width
           characters are rendered into two consecutive character containers.
        """
        data = data.translate(
            self.g1_charset if self.charset else self.g0_charset)

        # Fetch these attributes to avoid a lookup on each iteration
        # of the for-loop.
        # These attributes are expected to be constant across all the
        # execution of self.draw()
        columns = self.columns
        cursor = self.cursor
        buffer = self._buffer
        attrs = cursor.attrs
        mode = self.mode
        style = attrs.style

        # Note: checking for IRM here makes sense because it would be
        # checked on every char in data otherwise.
        # Checking DECAWM, on the other hand, not necessary is a good
        # idea because it only matters if cursor_x == columns (unlikely)
        is_IRM_set = mo.IRM in mode
        DECAWM = mo.DECAWM

        # The following are attributes expected to change infrequently
        # so we fetch them here and update accordingly if necessary
        cursor_x = cursor.x
        cursor_y = cursor.y
        line = buffer.line_at(cursor_y)

        write_data = line.write_data
        char_at = line.char_at
        for char in data:
            char_width = wcwidth(char)

            # If this was the last column in a line and auto wrap mode is
            # enabled, move the cursor to the beginning of the next line,
            # otherwise replace characters already displayed with newly
            # entered.
            if cursor_x >= columns:
                if DECAWM in mode:
                    self.dirty.add(cursor_y)
                    self.carriage_return()
                    self.linefeed()

                    # carriage_return implies cursor.x = 0 so we update cursor_x
                    # This also puts the cursor_x back into the screen if before
                    # cursor_x was outside (cursor_x > columns). See the comments
                    # at the end of the for-loop
                    cursor_x = 0

                    # linefeed may update cursor.y so we update cursor_y and
                    # the current line accordingly.
                    cursor_y = cursor.y
                    line = buffer.line_at(cursor_y)
                    write_data = line.write_data
                    char_at = line.char_at
                elif char_width > 0:
                    # Move the cursor_x back enough to make room for
                    # the new char.
                    # This indirectly fixes the case of cursor_x > columns putting
                    # the cursor_x back to the screen.
                    cursor_x = columns - char_width
                else:
                    # Ensure that cursor_x = min(cursor_x, columns) in the case
                    # that wcwidth returned 0 or negative and the flow didn't enter
                    # in any of the branches above.
                    # See the comments at the end of the for-loop
                    cursor_x = columns

            # If Insert mode is set, new characters move old characters to
            # the right, otherwise terminal is in Replace mode and new
            # characters replace old characters at cursor position.
            if is_IRM_set and char_width > 0:
                # update the real cursor so insert_characters() can use
                # an updated (and correct) value of it
                cursor.x = cursor_x
                self.insert_characters(char_width)

            if char_width == 1:
                write_data(cursor_x, char, char_width, style)
            elif char_width == 2:
                # A two-cell character has a stub slot after it.
                write_data(cursor_x, char, char_width, style)
                if cursor_x + 1 < columns:
                    write_data(cursor_x+1, "", 0, style)
            elif char_width == 0 and unicodedata.combining(char):
                # A zero-cell character is combined with the previous
                # character either on this or preceding line.
                # Because char's width is zero, this will not change the width
                # of the previous character.
                if cursor_x:
                    last = char_at(cursor_x - 1)
                    normalized = unicodedata.normalize("NFC", last.data + char)
                    last.data = normalized
                elif cursor_y:
                    last = buffer.line_at(cursor_y - 1).char_at(columns - 1)
                    normalized = unicodedata.normalize("NFC", last.data + char)
                    last.data = normalized
            else:
                break  # Unprintable character or doesn't advance the cursor.

            # .. note:: We can't use :meth:`cursor_forward()`, because that
            #           way, we'll never know when to linefeed.
            #
            # Note: cursor_x may leave outside the screen if cursor_x > columns
            # but this is going to be fixed in the next iteration or at the end
            # of the draw() method
            cursor_x += char_width

        self.dirty.add(cursor_y)

        # Update the real cursor fixing the cursor_x to be
        # within the limits of the screen
        if cursor_x > columns:
            cursor.x = columns
        else:
            cursor.x = cursor_x
        cursor.y = cursor_y

    def set_title(self, param):
        """Set terminal title.

        .. note:: This is an XTerm extension supported by the Linux terminal.
        """
        self.title = param

    def set_icon_name(self, param):
        """Set icon name.

        .. note:: This is an XTerm extension supported by the Linux terminal.
        """
        self.icon_name = param

    def carriage_return(self):
        """Move the cursor to the beginning of the current line."""
        self.cursor.x = 0

    def index(self):
        """Move the cursor down one line in the same column. If the
        cursor is at the last line, create a new line at the bottom.
        """
        top, bottom = self.margins
        if self.cursor.y == bottom:
            buffer = self._buffer
            pop = buffer.pop

            non_empty_y = sorted(buffer)
            begin = bisect_left(non_empty_y, top + 1)
            end = bisect_right(non_empty_y, bottom, begin)

            # the top line must be unconditionally removed
            # this pop is required because it may happen that
            # the next line (top + 1) is empty and therefore
            # the for-loop above didn't overwrite the line before
            # (top + 1 - 1, aka top)
            pop(top, None)

            to_move = non_empty_y[begin:end]
            for y in to_move:
                buffer[y-1] = pop(y)

            # TODO: mark only the lines within margins?
            # we could mark "(y-1, y) for y in to_move"
            self.dirty.update(range(self.lines))
        else:
            self.cursor_down()

    def reverse_index(self):
        """Move the cursor up one line in the same column. If the cursor
        is at the first line, create a new line at the top.
        """
        top, bottom = self.margins
        if self.cursor.y == top:
            buffer = self._buffer
            pop = buffer.pop

            non_empty_y = sorted(buffer)
            begin = bisect_left(non_empty_y, top)
            end = bisect_right(non_empty_y, bottom - 1, begin)

            # the bottom line must be unconditionally removed
            # this pop is required because it may happen that
            # the previous line (bottom - 1) is empty and therefore
            # the for-loop above didn't overwrite the line after
            # (bottom - 1 + 1, aka bottom)
            pop(bottom, None)

            to_move = non_empty_y[begin:end]
            for y in reversed(to_move):
                buffer[y+1] = pop(y)

            # TODO: mark only the lines within margins?
            # we could mark "(y+1, y) for y in to_move"
            self.dirty.update(range(self.lines))

        else:
            self.cursor_up()

    def linefeed(self):
        """Perform an index and, if :data:`~pyte.modes.LNM` is set, a
        carriage return.
        """
        self.index()

        if mo.LNM in self.mode:
            self.carriage_return()

    def tab(self):
        """Move to the next tab space, or the end of the screen if there
        aren't anymore left.
        """
        tabstops = sorted(self.tabstops)

        # use bisect_right because self.cursor.x must not
        # be included
        at = bisect_right(tabstops, self.cursor.x)
        if at == len(tabstops):
            # no tabstops found, set the x to the end of the screen
            self.cursor.x = self.columns - 1
        else:
            self.cursor.x = tabstops[at]

    def backspace(self):
        """Move cursor to the left one or keep it in its position if
        it's at the beginning of the line already.
        """
        self.cursor_back()

    def save_cursor(self):
        """Push the current cursor position onto the stack."""
        self.savepoints.append(Savepoint(copy.deepcopy(self.cursor),
                                         self.g0_charset,
                                         self.g1_charset,
                                         self.charset,
                                         mo.DECOM in self.mode,
                                         mo.DECAWM in self.mode))

    def restore_cursor(self):
        """Set the current cursor position to whatever cursor is on top
        of the stack.
        """
        if self.savepoints:
            savepoint = self.savepoints.pop()

            self.g0_charset = savepoint.g0_charset
            self.g1_charset = savepoint.g1_charset
            self.charset = savepoint.charset

            if savepoint.origin:
                self.set_mode(mo.DECOM)
            if savepoint.wrap:
                self.set_mode(mo.DECAWM)

            self.cursor = savepoint.cursor
            self.ensure_hbounds()
            self.ensure_vbounds(use_margins=True)
        else:
            # If nothing was saved, the cursor moves to home position;
            # origin mode is reset. :todo: DECAWM?
            self.reset_mode(mo.DECOM)
            self.cursor_position()

    def insert_lines(self, count=None):
        """Insert the indicated # of lines at line with cursor. Lines
        displayed **at** and below the cursor move down. Lines moved
        past the bottom margin are lost.

        :param count: number of lines to insert.
        """
        count = count or 1
        top, bottom = self.margins

        # If cursor is outside scrolling margins it -- do nothin'.
        if top <= self.cursor.y <= bottom:
            self.dirty.update(range(self.cursor.y, self.lines))

            # the following algorithm is similar to the one found
            # in insert_characters except that operates over
            # the lines (y range) and not the chars (x range)
            buffer = self._buffer
            pop = buffer.pop
            non_empty_y = sorted(buffer)
            begin = bisect_left(non_empty_y, self.cursor.y)
            end = bisect_left(non_empty_y, (bottom + 1) - count)

            to_move = reversed(non_empty_y[begin:end])

            next_y = (bottom + 1) - count
            for y in to_move:
                for z in range(y + 1 + count, next_y + count):
                    pop(z, None)

                next_y = y
                buffer[y + count] = pop(y)

            for z in range(self.cursor.y, next_y + count):
                pop(z, None)

            self.carriage_return()

    def delete_lines(self, count=None):
        """Delete the indicated # of lines, starting at line with
        cursor. As lines are deleted, lines displayed below cursor
        move up. Lines added to bottom of screen have spaces with same
        character attributes as last line moved up.

        :param int count: number of lines to delete.
        """
        count = count or 1
        top, bottom = self.margins

        # If cursor is outside scrolling margins -- do nothin'.
        if top <= self.cursor.y <= bottom:
            self.dirty.update(range(self.cursor.y, self.lines))

            buffer = self._buffer
            pop = buffer.pop
            non_empty_y = sorted(buffer)
            begin = bisect_left(non_empty_y, self.cursor.y + count)
            end = bisect_left(non_empty_y, bottom + 1)

            to_move = non_empty_y[begin:end]

            prev_y = self.cursor.y + count - 1
            for y in to_move:
                for z in range(prev_y + 1 - count, y - count):
                    pop(z, None)

                prev_y = y
                buffer[y - count] = pop(y)

            for z in range(prev_y + 1 - count, min(prev_y + 1, bottom + 1)):
                pop(z, None)

            self.carriage_return()

    def insert_characters(self, count=None):
        """Insert the indicated # of blank characters at the cursor
        position. The cursor does not move and remains at the beginning
        of the inserted blank characters. Data on the line is shifted
        forward.

        :param int count: number of characters to insert.
        """
        self.dirty.add(self.cursor.y)

        count = count or 1
        line = self._buffer.get(self.cursor.y)

        # if there is no line (aka the line is empty), then don't do
        # anything as insert_characters only moves the chars within
        # the line but does not write anything new.
        if not line:
            return

        pop = line.pop

        # Note: the following is optimized for the case of long lines
        # that are not very densely populated, the amount of count
        # to insert is small and the cursor is not very close to the right
        # end.
        non_empty_x = sorted(line)
        begin = bisect_left(non_empty_x, self.cursor.x)
        end = bisect_left(non_empty_x, self.columns - count)

        to_move = reversed(non_empty_x[begin:end])

        # cursor.x
        # |
        # V    to_move
        # |---------------|
        #   0   1   x   3   4   5      count = 2  (x means empty)
        #
        #   x   x   0   1   4   3      (first for-loop without the inner loop: the "4" is wrong)
        #
        #   x   x   0   1   x   3      (first for-loop with the inner loop: the "4" is removed)
        next_x = self.columns - count
        for x in to_move:
            # Notice how if (x + 1) == (next_x) then you know
            # that no empty char are in between this x and the next one
            # and therefore the range() loop gets empty.
            # In other cases, (x + 1) < (next_x)
            for z in range(x + 1 + count, next_x + count):
                pop(z, None)

            # it may look weird but the current "x" is the "next_x"
            # of the next iteration because we are iterating to_move
            # backwards
            next_x = x
            line[x + count] = pop(x)

        # between the cursor.x and the last moved char
        # we may have that should be emptied
        for z in range(self.cursor.x, next_x + count):
            pop(z, None)


    def delete_characters(self, count=None):
        """Delete the indicated # of characters, starting with the
        character at cursor position. When a character is deleted, all
        characters to the right of cursor move left. Character attributes
        move with the characters.

        :param int count: number of characters to delete.
        """
        self.dirty.add(self.cursor.y)

        count = count or 1
        line = self._buffer.get(self.cursor.y)

        # if there is no line (aka the line is empty), then don't do
        # anything as delete_characters  only moves the chars within
        # the line but does not write anything new except a default char
        if not line:
            return

        pop = line.pop

        non_empty_x = sorted(line)
        begin = bisect_left(non_empty_x, self.cursor.x + count)

        to_move = non_empty_x[begin:]

        # cursor.x
        #   |
        #   |          to_move
        #   V     |---------------|
        #   0   1   x   3   4   x      count = 2  (x means empty)
        #
        #   0   3   4   3   x   x
        #
        #   x   3   4   x   x   x
        prev_x = self.cursor.x + count - 1
        for x in to_move:
            # Notice how if (x - 1) == (prev_x) then you know
            # that no empty char are in between this x and the prev one
            # and therefore the range() loop gets empty.
            # In other cases, (prev_x + 1) > (x)
            for z in range(prev_x + 1 - count, x - count):
                pop(z, None)

            prev_x = x
            line[x - count] = pop(x)

        # this delete from the last written to the last read
        for z in range(prev_x + 1 - count, prev_x + 1):
            pop(z, None)

    def erase_characters(self, count=None):
        """Erase the indicated # of characters, starting with the
        character at cursor position. Character attributes are set
        cursor attributes. The cursor remains in the same position.

        :param int count: number of characters to erase.

        .. note::

           Using cursor attributes for character attributes may seem
           illogical, but if recall that a terminal emulator emulates
           a type writer, it starts to make sense. The only way a type
           writer could erase a character is by typing over it.
        """
        self.dirty.add(self.cursor.y)
        count = count or 1

        line = self._buffer.line_at(self.cursor.y)

        # If the line's default char is equivalent to our cursor, overwriting
        # a char in the line is equivalent to delete it if from the line
        if line.default == self.cursor.attrs:
            pop = line.pop
            non_empty_x = sorted(line)
            begin = bisect_left(non_empty_x, self.cursor.x)
            end = bisect_left(non_empty_x, self.cursor.x + count, begin)

            list(map(pop, non_empty_x[begin:end]))

            # the line may end up being empty, delete it from the buffer (*)
            if not line:
                del self._buffer[self.cursor.y]

        else:
            write_data = line.write_data
            data = self.cursor.attrs.data
            width = self.cursor.attrs.width
            style = self.cursor.attrs.style
            # a full range scan is required and not a sparse scan
            # because we were asked to *write* on that full range
            for x in range(self.cursor.x,
                           min(self.cursor.x + count, self.columns)):
                write_data(x, data, width, style)

    def erase_in_line(self, how=0, private=False):
        """Erase a line in a specific way.

        Character attributes are set to cursor attributes.

        :param int how: defines the way the line should be erased in:

            * ``0`` -- Erases from cursor to end of line, including cursor
              position.
            * ``1`` -- Erases from beginning of line to cursor,
              including cursor position.
            * ``2`` -- Erases complete line.
        :param bool private: when ``True`` only characters marked as
                             erasable are affected **not implemented**.
        """
        self.dirty.add(self.cursor.y)
        if how == 0:
            low, high = self.cursor.x, self.columns
        elif how == 1:
            low, high = 0, (self.cursor.x + 1)
        elif how == 2:
            low, high = 0, self.columns

        line = self._buffer.line_at(self.cursor.y)

        # If the line's default char is equivalent to our cursor, overwriting
        # a char in the line is equivalent to delete it if from the line
        if line.default == self.cursor.attrs:
            pop = line.pop
            non_empty_x = sorted(line)
            begin = bisect_left(non_empty_x, low)
            end = bisect_left(non_empty_x, high, begin)

            list(map(pop, non_empty_x[begin:end]))

            # the line may end up being empty, delete it from the buffer (*)
            if not line:
                del self._buffer[self.cursor.y]

        else:
            write_data = line.write_data
            data = self.cursor.attrs.data
            width = self.cursor.attrs.width
            style = self.cursor.attrs.style
            # a full range scan is required and not a sparse scan
            # because we were asked to *write* on that full range
            for x in range(low, high):
                write_data(x, data, width, style)

    def erase_in_display(self, how=0, *args, **kwargs):
        """Erases display in a specific way.

        Character attributes are set to cursor attributes.

        :param int how: defines the way the line should be erased in:

            * ``0`` -- Erases from cursor to end of screen, including
              cursor position.
            * ``1`` -- Erases from beginning of screen to cursor,
              including cursor position.
            * ``2`` and ``3`` -- Erases complete display. All lines
              are erased and changed to single-width. Cursor does not
              move.
        :param bool private: when ``True`` only characters marked as
                             erasable are affected **not implemented**.

        .. versionchanged:: 0.8.1

           The method accepts any number of positional arguments as some
           ``clear`` implementations include a ``;`` after the first
           parameter causing the stream to assume a ``0`` second parameter.
        """
        if how == 0:
            top, bottom = self.cursor.y + 1, self.lines
        elif how == 1:
            top, bottom = 0, self.cursor.y
        elif how == 2 or how == 3:
            top, bottom = 0, self.lines

        buffer = self._buffer

        self.dirty.update(range(top, bottom))

        # if we were requested to clear the whole screen and
        # the cursor's attrs are the same than the screen's default
        # then this is equivalent to delete all the lines from the buffer
        if (how == 2 or how == 3) and self.default_char == self.cursor.attrs:
            buffer.clear()
            return

        # Remove the lines from the buffer as this is equivalent
        # to overwrite each char in them with the space character
        # (screen.default_char).
        # If a deleted line is then requested, a new line will
        # be added with screen.default_char as its default char
        if self.default_char == self.cursor.attrs:
            pop = buffer.pop
            non_empty_y = sorted(buffer)
            begin = bisect_left(non_empty_y, top)  # inclusive
            end = bisect_left(non_empty_y, bottom, begin) # exclusive

            list(map(pop, non_empty_y[begin:end]))

        else:
            data = self.cursor.attrs.data
            width = self.cursor.attrs.width
            style = self.cursor.attrs.style
            for y in range(top, bottom):
                line = buffer.line_at(y)
                write_data = line.write_data
                for x in range(0, self.columns):
                    write_data(x, data, width, style)

        if how == 0 or how == 1:
            self.erase_in_line(how)

    def set_tab_stop(self):
        """Set a horizontal tab stop at cursor position."""
        self.tabstops.add(self.cursor.x)

    def clear_tab_stop(self, how=0):
        """Clear a horizontal tab stop.

        :param int how: defines a way the tab stop should be cleared:

            * ``0`` or nothing -- Clears a horizontal tab stop at cursor
              position.
            * ``3`` -- Clears all horizontal tab stops.
        """
        if how == 0:
            # Clears a horizontal tab stop at cursor position, if it's
            # present, or silently fails if otherwise.
            self.tabstops.discard(self.cursor.x)
        elif how == 3:
            self.tabstops.clear()  # Clears all horizontal tab stops.

    def ensure_hbounds(self):
        """Ensure the cursor is within horizontal screen bounds."""
        self.cursor.x = min(max(0, self.cursor.x), self.columns - 1)

    def ensure_vbounds(self, use_margins=None):
        """Ensure the cursor is within vertical screen bounds.

        :param bool use_margins: when ``True`` or when
                                 :data:`~pyte.modes.DECOM` is set,
                                 cursor is bounded by top and and bottom
                                 margins, instead of ``[0; lines - 1]``.
        """
        if (use_margins or mo.DECOM in self.mode):
            top, bottom = self.margins
        else:
            top, bottom = 0, self.lines - 1

        self.cursor.y = min(max(top, self.cursor.y), bottom)

    def cursor_up(self, count=None):
        """Move cursor up the indicated # of lines in same column.
        Cursor stops at top margin.

        :param int count: number of lines to skip.
        """
        top, _bottom = self.margins
        self.cursor.y = max(self.cursor.y - (count or 1), top)

    def cursor_up1(self, count=None):
        """Move cursor up the indicated # of lines to column 1. Cursor
        stops at bottom margin.

        :param int count: number of lines to skip.
        """
        self.cursor_up(count)
        self.carriage_return()

    def cursor_down(self, count=None):
        """Move cursor down the indicated # of lines in same column.
        Cursor stops at bottom margin.

        :param int count: number of lines to skip.
        """
        _top, bottom = self.margins
        self.cursor.y = min(self.cursor.y + (count or 1), bottom)

    def cursor_down1(self, count=None):
        """Move cursor down the indicated # of lines to column 1.
        Cursor stops at bottom margin.

        :param int count: number of lines to skip.
        """
        self.cursor_down(count)
        self.carriage_return()

    def cursor_back(self, count=None):
        """Move cursor left the indicated # of columns. Cursor stops
        at left margin.

        :param int count: number of columns to skip.
        """
        # Handle the case when we've just drawn in the last column
        # and would wrap the line on the next :meth:`draw()` call.
        if self.cursor.x == self.columns:
            self.cursor.x -= 1

        self.cursor.x -= count or 1
        self.ensure_hbounds()

    def cursor_forward(self, count=None):
        """Move cursor right the indicated # of columns. Cursor stops
        at right margin.

        :param int count: number of columns to skip.
        """
        self.cursor.x += count or 1
        self.ensure_hbounds()

    def cursor_position(self, line=None, column=None):
        """Set the cursor to a specific `line` and `column`.

        Cursor is allowed to move out of the scrolling region only when
        :data:`~pyte.modes.DECOM` is reset, otherwise -- the position
        doesn't change.

        :param int line: line number to move the cursor to.
        :param int column: column number to move the cursor to.
        """
        column = (column or 1) - 1
        line = (line or 1) - 1

        # If origin mode (DECOM) is set, line number are relative to
        # the top scrolling margin.
        if mo.DECOM in self.mode:
            line += self.margins.top

            # Cursor is not allowed to move out of the scrolling region.
            if not self.margins.top <= line <= self.margins.bottom:
                return

        self.cursor.x = column
        self.cursor.y = line
        self.ensure_hbounds()
        self.ensure_vbounds()

    def cursor_to_column(self, column=None):
        """Move cursor to a specific column in the current line.

        :param int column: column number to move the cursor to.
        """
        self.cursor.x = (column or 1) - 1
        self.ensure_hbounds()

    def cursor_to_line(self, line=None):
        """Move cursor to a specific line in the current column.

        :param int line: line number to move the cursor to.
        """
        self.cursor.y = (line or 1) - 1

        # If origin mode (DECOM) is set, line number are relative to
        # the top scrolling margin.
        if mo.DECOM in self.mode:
            self.cursor.y += self.margins.top

            # FIXME: should we also restrict the cursor to the scrolling
            # region?

        self.ensure_vbounds()

    def bell(self, *args):
        """Bell stub -- the actual implementation should probably be
        provided by the end-user.
        """

    def alignment_display(self):
        """Fills screen with uppercase E's for screen focus and alignment."""
        self.dirty.update(range(self.lines))
        style = self._default_style
        for y in range(self.lines):
            line = self._buffer.line_at(y)
            for x in range(self.columns):
                line.write_data(x, "E", wcwidth("E"), style)

    def select_graphic_rendition(self, *attrs):
        """Set display attributes.

        :param list attrs: a list of display attributes to set.

        .. note::

        If `disable_display_graphic` was set, this method
        set the cursor's attributes to the default char's attributes
        ignoring all the parameters.
        Equivalent to `screen.select_graphic_rendition(0)`.
        """
        replace = {}

        # Fast path for resetting all attributes.
        if not attrs or attrs == (0, ) or self.disabled_display_graphic:
            self.cursor.attrs = self.default_char
            return
        else:
            attrs = list(reversed(attrs))

        while attrs:
            attr = attrs.pop()
            if attr == 0:
                # Reset all attributes.
                replace.update(self.default_char.style._asdict())
            elif attr in g.FG_ANSI:
                replace["fg"] = g.FG_ANSI[attr]
            elif attr in g.BG:
                replace["bg"] = g.BG_ANSI[attr]
            elif attr in g.TEXT:
                attr = g.TEXT[attr]
                replace[attr[1:]] = attr.startswith("+")
            elif attr in g.FG_AIXTERM:
                replace.update(fg=g.FG_AIXTERM[attr])
            elif attr in g.BG_AIXTERM:
                replace.update(bg=g.BG_AIXTERM[attr])
            elif attr in (g.FG_256, g.BG_256):
                key = "fg" if attr == g.FG_256 else "bg"
                try:
                    n = attrs.pop()
                    if n == 5:    # 256.
                        m = attrs.pop()
                        replace[key] = g.FG_BG_256[m]
                    elif n == 2:  # 24bit.
                        # This is somewhat non-standard but is nonetheless
                        # supported in quite a few terminals. See discussion
                        # here https://gist.github.com/XVilka/8346728.
                        replace[key] = "{0:02x}{1:02x}{2:02x}".format(
                            attrs.pop(), attrs.pop(), attrs.pop())
                except IndexError:
                    pass

        self.cursor.attrs.style = self.cursor.attrs.style._replace(**replace)

    def report_device_attributes(self, mode=0, **kwargs):
        """Report terminal identity.

        .. versionadded:: 0.5.0

        .. versionchanged:: 0.7.0

           If ``private`` keyword argument is set, the method does nothing.
           This behaviour is consistent with VT220 manual.
        """
        # We only implement "primary" DA which is the only DA request
        # VT102 understood, see ``VT102ID`` in ``linux/drivers/tty/vt.c``.
        if mode == 0 and not kwargs.get("private"):
            self.write_process_input(ctrl.CSI + "?6c")

    def report_device_status(self, mode):
        """Report terminal status or cursor position.

        :param int mode: if 5 -- terminal status, 6 -- cursor position,
                         otherwise a noop.

        .. versionadded:: 0.5.0
        """
        if mode == 5:    # Request for terminal status.
            self.write_process_input(ctrl.CSI + "0n")
        elif mode == 6:  # Request for cursor position.
            x = self.cursor.x + 1
            y = self.cursor.y + 1

            # "Origin mode (DECOM) selects line numbering."
            if mo.DECOM in self.mode:
                y -= self.margins.top
            self.write_process_input(ctrl.CSI + "{0};{1}R".format(y, x))

    def write_process_input(self, data):
        """Write data to the process running inside the terminal.

        By default is a noop.

        :param str data: text to write to the process ``stdin``.

        .. versionadded:: 0.5.0
        """

    def debug(self, *args, **kwargs):
        """Endpoint for unrecognized escape sequences.

        By default is a noop.
        """


class DiffScreen(Screen):
    """
    A screen subclass, which maintains a set of dirty lines in its
    :attr:`dirty` attribute. The end user is responsible for emptying
    a set, when a diff is applied.

    .. deprecated:: 0.7.0

       The functionality contained in this class has been merged into
       :class:`~pyte.screens.Screen` and will be removed in 0.8.0.
       Please update your code accordingly.
    """
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "The functionality of ``DiffScreen` has been merged into "
            "``Screen`` and will be removed in 0.8.0. Please update "
            "your code accordingly.", DeprecationWarning)

        super(DiffScreen, self).__init__(*args, **kwargs)


History = namedtuple("History", "top bottom ratio size position")


class HistoryScreen(Screen):
    """A :class:`~pyte.screens.Screen` subclass, which keeps track
    of screen history and allows pagination. This is not linux-specific,
    but still useful; see page 462 of VT520 User's Manual.

    :param int history: total number of history lines to keep; is split
                        between top and bottom queues.
    :param int ratio: defines how much lines to scroll on :meth:`next_page`
                      and :meth:`prev_page` calls.

    .. attribute:: history

       A pair of history queues for top and bottom margins accordingly;
       here's the overall screen structure::

            [ 1: .......]
            [ 2: .......]  <- top history
            [ 3: .......]
            ------------
            [ 4: .......]  s
            [ 5: .......]  c
            [ 6: .......]  r
            [ 7: .......]  e
            [ 8: .......]  e
            [ 9: .......]  n
            ------------
            [10: .......]
            [11: .......]  <- bottom history
            [12: .......]

    .. note::

       Don't forget to update :class:`~pyte.streams.Stream` class with
       appropriate escape sequences -- you can use any, since pagination
       protocol is not standardized, for example::

           Stream.escape["N"] = "next_page"
           Stream.escape["P"] = "prev_page"
    """
    _wrapped = set(Stream.events)
    _wrapped.update(["next_page", "prev_page"])

    def __init__(self, columns, lines, history=100, ratio=.5,
                 track_dirty_lines=True, disable_display_graphic=False):
        self.history = History(deque(maxlen=history),
                               deque(maxlen=history),
                               float(ratio),
                               history,
                               history)

        super(HistoryScreen, self).__init__(columns, lines,
                track_dirty_lines=track_dirty_lines,
                disable_display_graphic=disable_display_graphic)

    def _make_wrapper(self, event, handler):
        def inner(*args, **kwargs):
            self.before_event(event)
            result = handler(*args, **kwargs)
            self.after_event(event)
            return result
        return inner

    def __getattribute__(self, attr):
        value = super(HistoryScreen, self).__getattribute__(attr)
        if attr in HistoryScreen._wrapped:
            return HistoryScreen._make_wrapper(self, attr, value)
        else:
            return value

    def before_event(self, event):
        """Ensure a screen is at the bottom of the history buffer.

        :param str event: event name, for example ``"linefeed"``.
        """
        if event not in ["prev_page", "next_page"]:
            while self.history.position < self.history.size:
                self.next_page()

    def after_event(self, event):
        """Ensure all lines on a screen have proper width (:attr:`columns`).

        Extra characters are truncated, missing characters are filled
        with whitespace.

        :param str event: event name, for example ``"linefeed"``.
        """
        if event in ["prev_page", "next_page"]:
            columns = self.columns
            for line in self._buffer.values():
                pop = line.pop
                non_empty_x = sorted(line)
                begin = bisect_left(non_empty_x, columns)

                list(map(pop, non_empty_x[begin:]))

        # If we're at the bottom of the history buffer and `DECTCEM`
        # mode is set -- show the cursor.
        self.cursor.hidden = not (
            self.history.position == self.history.size and
            mo.DECTCEM in self.mode
        )

    def _reset_history(self):
        self.history.top.clear()
        self.history.bottom.clear()
        self.history = self.history._replace(position=self.history.size)

    def reset(self):
        """Overloaded to reset screen history state: history position
        is reset to bottom of both queues;  queues themselves are
        emptied.
        """
        super(HistoryScreen, self).reset()
        self._reset_history()

    def erase_in_display(self, how=0, *args, **kwargs):
        """Overloaded to reset history state."""
        super(HistoryScreen, self).erase_in_display(how, *args, **kwargs)

        if how == 3:
            self._reset_history()

    def index(self):
        """Overloaded to update top history with the removed lines."""
        top, bottom = self.margins

        if self.cursor.y == bottom:
            self.history.top.append(self.buffer[top])

        super(HistoryScreen, self).index()

    def reverse_index(self):
        """Overloaded to update bottom history with the removed lines."""
        top, bottom = self.margins

        if self.cursor.y == top:
            self.history.bottom.append(self.buffer[bottom])

        super(HistoryScreen, self).reverse_index()

    def prev_page(self):
        """Move the screen page up through the history buffer. Page
        size is defined by ``history.ratio``, so for instance
        ``ratio = .5`` means that half the screen is restored from
        history on page switch.
        """
        if self.history.position > self.lines and self.history.top:
            mid = min(len(self.history.top),
                      int(math.ceil(self.lines * self.history.ratio)))

            bufferview = self.buffer
            buffer = self._buffer
            pop = buffer.pop

            self.history.bottom.extendleft(
                bufferview[y]
                for y in range(self.lines - 1, self.lines - mid - 1, -1)
                )

            self.history = self.history \
                ._replace(position=self.history.position - mid)

            non_empty_y = sorted(buffer)
            end = bisect_left(non_empty_y, self.lines - mid)

            to_move = reversed(non_empty_y[:end])

            #      to_move
            # |---------------|
            #   0   1   x   3   4   5      mid = 2  (x means empty)
            #
            #   0   1   0   1   4   3      (first for-loop without the inner loop: the "4" is wrong)
            #
            #   0   1   0   1   x   3      (first for-loop with the inner loop: the "4" is removed)
            #
            #   P   P   0   1   x   3      (after third for-loop, P are from history.top)
            next_y = self.lines - mid
            for y in to_move:
                # Notice how if (y + 1) == (next_y) then you know
                # that no empty lines are in between this y and the next one
                # and therefore the range() loop gets empty.
                # In other cases, (y + 1) < (next_y)
                for z in range(y + 1 + mid, next_y + mid):
                    pop(z, None)

                # it may look weird but the current "y" is the "next_y"
                # of the next iteration because we are iterating to_move
                # backwards
                next_y = y
                buffer[y + mid] = buffer[y]

            # between the last moved line and the begin of the page
            # we may have lines that should be emptied
            for z in range(0 + mid, next_y + mid):
                pop(z, None)

            for y in range(mid - 1, -1, -1):
                line = self.history.top.pop()._line
                if line:
                    # note: empty lines are not added as they are
                    # the default for non-existent entries in buffer
                    buffer[y] = line
                else:
                    # because empty lines are not added we need to ensure
                    # that the old lines in that position become empty
                    # anyways (aka, we remove the old ones)
                    pop(y, None)

            self.dirty.clear()
            self.dirty.update(range(self.lines))

    def next_page(self):
        """Move the screen page down through the history buffer."""
        if self.history.position < self.history.size and self.history.bottom:
            mid = min(len(self.history.bottom),
                      int(math.ceil(self.lines * self.history.ratio)))

            bufferview = self.buffer
            buffer = self._buffer
            pop = buffer.pop

            self.history.top.extend(
                    bufferview[y]
                    for y in range(mid)
                    )

            self.history = self.history \
                ._replace(position=self.history.position + mid)

            non_empty_y = sorted(buffer)
            begin = bisect_left(non_empty_y, mid)

            to_move = non_empty_y[begin:]

            #              to_move
            #         |---------------|
            #   0   1   2   x   4   5      mid = 2
            #
            #   2   1   4   5   4   5
            #
            #   2   3   4   5   P   P      (final result)

            prev_y = mid - 1
            for y in to_move:
                # Notice how if (prev_y + 1) == (y) then you know
                # that no empty lines are in between and therefore
                # the range() loop gets empty.
                # In other cases, (prev_y + 1) > (y)
                for z in range(prev_y + 1 - mid, y - mid):
                    pop(z, None)

                prev_y = y
                buffer[y - mid] = buffer[y]

            for z in range(prev_y + 1 - mid, self.lines - mid):
                pop(z, None)

            for y in range(self.lines - mid, self.lines):
                line = self.history.bottom.popleft()._line
                if line:
                    buffer[y] = line
                else:
                    # because empty lines are not added we need to ensure
                    # that the old lines in that position become empty
                    # anyways (aka, we remove the old ones)
                    pop(y, None)

            self.dirty.clear()
            self.dirty.update(range(self.lines))


class DebugEvent(namedtuple("Event", "name args kwargs")):
    """Event dispatched to :class:`~pyte.screens.DebugScreen`.

    .. warning::

       This is developer API with no backward compatibility guarantees.
       Use at your own risk!
    """
    @staticmethod
    def from_string(line):
        return DebugEvent(*json.loads(line))

    def __str__(self):
        return json.dumps(self)

    def __call__(self, screen):
        """Execute this event on a given ``screen``."""
        return getattr(screen, self.name)(*self.args, **self.kwargs)


class DebugScreen:
    r"""A screen which dumps a subset of the received events to a file.

    >>> import io
    >>> with io.StringIO() as buf:
    ...     stream = Stream(DebugScreen(to=buf))
    ...     stream.feed("\x1b[1;24r\x1b[4l\x1b[24;1H\x1b[0;10m")
    ...     print(buf.getvalue())
    ...
    ... # doctest: +NORMALIZE_WHITESPACE
    ["set_margins", [1, 24], {}]
    ["reset_mode", [4], {}]
    ["cursor_position", [24, 1], {}]
    ["select_graphic_rendition", [0, 10], {}]

    :param file to: a file-like object to write debug information to.
    :param list only: a list of events you want to debug (empty by
                      default, which means -- debug all events).

    .. warning::

       This is developer API with no backward compatibility guarantees.
       Use at your own risk!
    """
    def __init__(self, to=sys.stderr, only=()):
        self.to = to
        self.only = only

    def only_wrapper(self, attr):
        def wrapper(*args, **kwargs):
            self.to.write(str(DebugEvent(attr, args, kwargs)))
            self.to.write(str(os.linesep))

        return wrapper

    def __getattribute__(self, attr):
        if attr not in Stream.events:
            return super(DebugScreen, self).__getattribute__(attr)
        elif not self.only or attr in self.only:
            return self.only_wrapper(attr)
        else:
            return lambda *args, **kwargs: None
