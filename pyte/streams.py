# -*- coding: utf-8 -*-
"""
    pyte.streams
    ~~~~~~~~~~~~

    This module provides three stream implementations with different
    features; for starters, here's a quick example of how streams are
    typically used:

    >>> import pyte
    >>> screen = pyte.Screen(80, 24)
    >>> stream = pyte.Stream(screen)
    >>> stream.feed("\x1b[5B")  # Move the cursor down 5 rows.
    >>> screen.cursor.y
    5

    :copyright: (c) 2011-2012 by Selectel.
    :copyright: (c) 2012-2017 by pyte authors and contributors,
                    see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import absolute_import, unicode_literals

import codecs
import itertools
import re
import warnings
from collections import defaultdict

from . import control as ctrl, escape as esc
from .compat import pass_through_str


class Stream(object):
    """A stream is a state machine that parses a stream of bytes and
    dispatches events based on what it sees.

    :param pyte.screens.Screen screen: a screen to dispatch events to.
    :param bool strict: check if a given screen implements all required
                        events.

    .. note::

       Stream only accepts text as input, but if for some reason
       you need to feed it with bytes, consider using
       :class:`~pyte.streams.ByteStream` instead.

    .. versionchanged 0.6.0::

       For performance reasons the binding between stream events and
       screen methods was made static. As a result, the stream **will
       not** dispatch events to methods added to screen **after** the
       stream was created.

    .. seealso::

        `man console_codes <http://linux.die.net/man/4/console_codes>`_
            For details on console codes listed bellow in :attr:`basic`,
            :attr:`escape`, :attr:`csi`, :attr:`sharp`.
    """

    #: Control sequences, which don't require any arguments.
    basic = {
        ctrl.BEL: "bell",
        ctrl.BS: "backspace",
        ctrl.HT: "tab",
        ctrl.LF: "linefeed",
        ctrl.VT: "linefeed",
        ctrl.FF: "linefeed",
        ctrl.CR: "carriage_return",
        ctrl.SO: "shift_out",
        ctrl.SI: "shift_in",
    }

    #: non-CSI escape sequences.
    escape = {
        esc.RIS: "reset",
        esc.IND: "index",
        esc.NEL: "linefeed",
        esc.RI: "reverse_index",
        esc.HTS: "set_tab_stop",
        esc.DECSC: "save_cursor",
        esc.DECRC: "restore_cursor",
    }

    #: "sharp" escape sequences -- ``ESC # <N>``.
    sharp = {
        esc.DECALN: "alignment_display",
    }

    #: CSI escape sequences -- ``CSI P1;P2;...;Pn <fn>``.
    csi = {
        esc.ICH: "insert_characters",
        esc.CUU: "cursor_up",
        esc.CUD: "cursor_down",
        esc.CUF: "cursor_forward",
        esc.CUB: "cursor_back",
        esc.CNL: "cursor_down1",
        esc.CPL: "cursor_up1",
        esc.CHA: "cursor_to_column",
        esc.CUP: "cursor_position",
        esc.ED: "erase_in_display",
        esc.EL: "erase_in_line",
        esc.IL: "insert_lines",
        esc.DL: "delete_lines",
        esc.DCH: "delete_characters",
        esc.ECH: "erase_characters",
        esc.HPR: "cursor_forward",
        esc.DA: "report_device_attributes",
        esc.VPA: "cursor_to_line",
        esc.VPR: "cursor_down",
        esc.HVP: "cursor_position",
        esc.TBC: "clear_tab_stop",
        esc.SM: "set_mode",
        esc.RM: "reset_mode",
        esc.SGR: "select_graphic_rendition",
        esc.DSR: "report_device_status",
        esc.DECSTBM: "set_margins",
        esc.HPA: "cursor_to_column"
    }

    #: A set of all events dispatched by the stream.
    events = frozenset(itertools.chain(
        basic.values(), escape.values(), sharp.values(), csi.values(),
        ["define_charset"],
        ["set_icon_name", "set_title"],  # OSC.
        ["draw", "debug"]))

    #: A regular expression pattern matching everything what can be
    #: considered plain text.
    _special = set([ctrl.ESC, ctrl.CSI_C1, ctrl.NUL, ctrl.DEL, ctrl.OSC_C1])
    _special.update(basic)
    _text_pattern = re.compile(
        "[^" + "".join(map(re.escape, _special)) + "]+")
    del _special

    def __init__(self, screen=None, strict=True):
        self.listener = None
        self.strict = strict
        self.use_utf8 = True

        if screen is not None:
            self.attach(screen)

    def attach(self, screen):
        """Adds a given screen to the listener queue.

        :param pyte.screens.Screen screen: a screen to attach to.
        """
        if self.listener is not None:
            warnings.warn("As of version 0.6.0 the listener queue is "
                          "restricted to a single element. Existing "
                          "listener {0} will be replaced."
                          .format(self.listener), DeprecationWarning)

        if self.strict:
            for event in self.events:
                if not hasattr(screen, event):
                    raise TypeError("{0} is missing {1}".format(screen, event))

        self.listener = screen
        self._parser = self._parser_fsm()
        self._taking_plain_text = next(self._parser)

    def detach(self, screen):
        """Remove a given screen from the listener queue and fails
        silently if it's not attached.

        :param pyte.screens.Screen screen: a screen to detach.
        """
        if screen is self.listener:
            self.listener = None

    def feed(self, data):
        """Consume some data and advances the state as necessary.

        :param str data: a blob of data to feed from.
        """
        send = self._parser.send
        draw = self.listener.draw
        match_text = self._text_pattern.match
        taking_plain_text = self._taking_plain_text

        length = len(data)
        offset = 0
        while offset < length:
            if taking_plain_text:
                match = match_text(data, offset)
                if match:
                    start, offset = match.span()
                    draw(data[start:offset])
                else:
                    taking_plain_text = False
            else:
                taking_plain_text = send(data[offset:offset + 1])
                offset += 1

        self._taking_plain_text = taking_plain_text

    def _parser_fsm(self):
        """An FSM implemented as a coroutine.

        This generator is not the most beautiful, but it is as performant
        as possible. When a process generates a lot of output, then this
        will be the bottleneck, because it processes just one character
        at a time.

        Don't change anything without profiling first.
        """
        basic = self.basic
        listener = self.listener
        draw = listener.draw
        debug = listener.debug

        ESC, CSI_C1 = ctrl.ESC, ctrl.CSI_C1
        OSC_C1 = ctrl.OSC_C1
        SP_OR_GT = ctrl.SP + ">"
        NUL_OR_DEL = ctrl.NUL + ctrl.DEL
        CAN_OR_SUB = ctrl.CAN + ctrl.SUB
        ALLOWED_IN_CSI = "".join([ctrl.BEL, ctrl.BS, ctrl.HT, ctrl.LF,
                                  ctrl.VT, ctrl.FF, ctrl.CR])
        OSC_TERMINATORS = set([ctrl.ST_C0, ctrl.ST_C1, ctrl.BEL])

        def create_dispatcher(mapping):
            return defaultdict(lambda: debug, dict(
                (event, getattr(listener, attr))
                for event, attr in mapping.items()))

        basic_dispatch = create_dispatcher(basic)
        sharp_dispatch = create_dispatcher(self.sharp)
        escape_dispatch = create_dispatcher(self.escape)
        csi_dispatch = create_dispatcher(self.csi)

        while True:
            # ``True`` tells ``Screen.feed`` that it is allowed to send
            # chunks of plain text directly to the listener, instead
            # of this generator.
            char = yield True

            if char == ESC:
                # Most non-VT52 commands start with a left-bracket after the
                # escape and then a stream of parameters and a command; with
                # a single notable exception -- :data:`escape.DECOM` sequence,
                # which starts with a sharp.
                #
                # .. versionchanged:: 0.4.10
                #
                #    For compatibility with Linux terminal stream also
                #    recognizes ``ESC % C`` sequences for selecting control
                #    character set. However, in the current version these
                #    are noop.
                char = yield
                if char == "[":
                    char = CSI_C1  # Go to CSI.
                elif char == "]":
                    char = OSC_C1  # Go to OSC.
                else:
                    if char == "#":
                        sharp_dispatch[(yield)]()
                    if char == "%":
                        self.select_other_charset((yield))
                    elif char in "()":
                        code = yield
                        if self.use_utf8:
                            continue

                        # See http://www.cl.cam.ac.uk/~mgk25/unicode.html#term
                        # for the why on the UTF-8 restriction.
                        listener.define_charset(code, mode=char)
                    else:
                        escape_dispatch[char]()
                    continue    # Don't go to CSI.

            if char in basic:
                # Ignore shifts in UTF-8 mode. See
                # http://www.cl.cam.ac.uk/~mgk25/unicode.html#term for
                # the why on UTF-8 restriction.
                if (char == ctrl.SI or char == ctrl.SO) and self.use_utf8:
                    continue

                basic_dispatch[char]()
            elif char == CSI_C1:
                # All parameters are unsigned, positive decimal integers, with
                # the most significant digit sent first. Any parameter greater
                # than 9999 is set to 9999. If you do not specify a value, a 0
                # value is assumed.
                #
                # .. seealso::
                #
                #    `VT102 User Guide <http://vt100.net/docs/vt102-ug/>`_
                #        For details on the formatting of escape arguments.
                #
                #    `VT220 Programmer Ref. <http://vt100.net/docs/vt220-rm/>`_
                #        For details on the characters valid for use as
                #        arguments.
                params = []
                current = ""
                private = False
                while True:
                    char = yield
                    if char == "?":
                        private = True
                    elif char in ALLOWED_IN_CSI:
                        basic_dispatch[char]()
                    elif char in SP_OR_GT:
                        pass  # Secondary DA is not supported atm.
                    elif char in CAN_OR_SUB:
                        # If CAN or SUB is received during a sequence, the
                        # current sequence is aborted; terminal displays
                        # the substitute character, followed by characters
                        # in the sequence received after CAN or SUB.
                        draw(char)
                        break
                    elif char.isdigit():
                        current += char
                    else:
                        params.append(min(int(current or 0), 9999))

                        if char == ";":
                            current = ""
                        else:
                            if private:
                                csi_dispatch[char](*params, private=True)
                            else:
                                csi_dispatch[char](*params)
                            break  # CSI is finished.
            elif char == OSC_C1:
                code = yield
                if code == "R":
                    continue  # Reset palette. Not implemented.
                elif code == "P":
                    continue  # Set palette. Not implemented.

                param = ""
                while True:
                    char = yield
                    if char == ESC:
                        char += yield
                    if char in OSC_TERMINATORS:
                        break
                    else:
                        param += char

                param = param[1:]  # Drop the ;.
                if code in "01":
                    listener.set_icon_name(param)
                if code in "02":
                    listener.set_title(param)
            elif char not in NUL_OR_DEL:
                draw(char)

    def select_other_charset(self, code):
        """Select other (non G0 or G1) charset.

        :param str code: character set code, should be a character from
                         ``"@G8"``, otherwise ignored.

        .. note:: We currently follow ``"linux"`` and only use this
                  command to switch from ISO-8859-1 to UTF-8 and back.

        .. versionadded:: 0.6.0

        .. seealso::

           `Standard ECMA-35, Section 15.4 \
           <http://ecma-international.org/publications/standards/Ecma-035.htm>`_
           for a description of VTXXX character set machinery.
        """
        # A noop since all input is Unicode-only.


class ByteStream(Stream):
    """A stream which takes bytes as input.

    Bytes are decoded to text using either UTF-8 (default) or the encoding
    selected via :meth:`~pyte.Stream.select_other_charset`.

    .. attribute:: use_utf8

       Assume the input to :meth:`~pyte.streams.ByteStream.feed` is encoded
       using UTF-8. Defaults to ``True``.
    """
    def __init__(self, *args, **kwargs):
        super(ByteStream, self).__init__(*args, **kwargs)

        self.utf8_decoder = codecs.getincrementaldecoder("utf-8")("replace")

    def feed(self, data):
        if self.use_utf8:
            data = self.utf8_decoder.decode(data)
        else:
            data = pass_through_str(data)

        super(ByteStream, self).feed(data)

    def select_other_charset(self, code):
        if code == "@":
            self.use_utf8 = False
            self.utf8_decoder.reset()
        elif code in "G8":
            self.use_utf8 = True
