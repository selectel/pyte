# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import sys

if sys.version_info[0] == 2:
    from cStringIO import StringIO
else:
    from io import StringIO

import pytest

from pyte import control as ctrl, escape as esc
from pyte.screens import Screen
from pyte.streams import Stream, ByteStream, DebugStream


class counter(object):
    def __init__(self):
        self.count = 0

    def __call__(self, *args, **kwargs):
        self.count += 1


class argcheck(counter):
    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        super(argcheck, self).__call__()


class argstore(object):
    def __init__(self):
        self.seen = []

    def __call__(self, *args):
        self.seen.extend(args)


def test_basic_sequences():
    screen = Screen(80, 24)
    stream = Stream(screen)

    for cmd, event in stream.escape.items():
        handler = counter()
        setattr(screen, event, handler)

        stream.feed(ctrl.ESC)
        assert not handler.count

        stream.feed(cmd)
        assert handler.count == 1

    # ``linefeed``s is somewhat an exception, there's three ways to
    # trigger it.
    handler = counter()

    screen.linefeed = handler
    stream.feed(ctrl.LF + ctrl.VT + ctrl.FF)

    assert handler.count == 3


def test_unknown_sequences():
    handler = argcheck()
    screen = Screen(80, 24)
    screen.debug = handler

    stream = Stream(screen)
    stream.feed(ctrl.CSI + "6;Z")
    assert handler.count == 1
    assert handler.args == (6, 0)
    assert handler.kwargs == {}


def test_non_csi_sequences():
    screen = Screen(80, 24)
    stream = Stream(screen)

    for cmd, event in stream.csi.items():
        # a) single param
        handler = argcheck()
        setattr(screen, event, handler)
        stream.feed(ctrl.ESC)

        stream.feed("[")
        stream.feed("5")
        stream.feed(cmd)

        assert handler.count == 1
        assert handler.args == (5, )

        # b) multiple params, and starts with CSI, not ESC [
        handler = argcheck()
        setattr(screen, event, handler)
        stream.feed(ctrl.CSI)
        stream.feed("5")
        stream.feed(";")
        stream.feed("12")
        stream.feed(cmd)

        assert handler.count == 1
        assert handler.args == (5, 12)


def test_mode_csi_sequences():
    bugger = counter()
    screen = Screen(80, 24)
    screen.debug = bugger

    stream = Stream(screen)

    # a) set_mode
    handler = argcheck()
    screen.set_mode = handler
    stream.feed(ctrl.CSI + "?9;2h")

    assert not bugger.count
    assert handler.count == 1
    assert handler.args == (9, 2)
    assert handler.kwargs == {"private": True}

    # a) reset_mode
    handler = argcheck()
    screen.reset_mode = handler
    stream.feed(ctrl.CSI + "?9;2l")

    assert not bugger.count
    assert handler.count == 1
    assert handler.args == (9, 2)


def test_missing_params():
    handler = argcheck()
    screen = Screen(80, 24)
    screen.cursor_position = handler

    stream = Stream(screen)
    stream.feed(ctrl.CSI + ";" + esc.HVP)
    assert handler.count == 1
    assert handler.args == (0, 0)


def test_overflow():
    handler = argcheck()
    screen = Screen(80, 24)
    screen.cursor_position = handler

    stream = Stream(screen)
    stream.feed(ctrl.CSI + "999999999999999;99999999999999" + esc.HVP)
    assert handler.count == 1
    assert handler.args == (9999, 9999)


def test_interrupt():
    bugger = argstore()
    handler = argcheck()

    screen = Screen(80, 24)
    screen.draw = bugger
    screen.cursor_position = handler

    stream = Stream(screen)
    stream.feed(ctrl.CSI + "10;" + ctrl.SUB + "10" + esc.HVP)

    assert not handler.count
    assert bugger.seen == [
        ctrl.SUB, "10" + esc.HVP
    ]


def test_control_characters():
    handler = argcheck()
    screen = Screen(80, 24)
    screen.cursor_position = handler

    stream = Stream(screen)
    stream.feed(ctrl.CSI + "10;\t\t\n\r\n10" + esc.HVP)

    assert handler.count == 1
    assert handler.args == (10, 10)


def test_debug_stream():
    tests = [
        (b"foo", "DRAW foo"),
        (b"\x1b[1;24r\x1b[4l\x1b[24;1H",
         "SET_MARGINS 1; 24\nRESET_MODE 4\nCURSOR_POSITION 24; 1"),
    ]

    for input, expected in tests:
        output = StringIO()
        stream = DebugStream(to=output)
        stream.feed(input)

        lines = [l.rstrip() for l in output.getvalue().splitlines()]
        assert lines == expected.splitlines()


def test_byte_stream():
    def validator(char):
        assert "\ufffd" not in char

    screen = Screen(80, 24)
    screen.draw = validator

    stream = ByteStream(screen, encodings=[("utf-8", "replace")])
    stream.feed("Garðabær".encode("utf-8"))


def test_byte_stream_failure():
    stream = ByteStream(Screen(80, 24), encodings=[("ascii", "strict")])
    with pytest.raises(ValueError):
        stream.feed("привет".encode("utf-8"))
