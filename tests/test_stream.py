# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import operator
import sys

if sys.version_info[0] == 2:
    from cStringIO import StringIO
else:
    from io import StringIO

import pytest

from pyte import ctrl, esc
from pyte.streams import DebugStream
from . import TestStream, TestByteStream


class counter(object):
    def __init__(self):
        self.count = 0

    def __call__(self, *args):
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
    stream = TestStream()

    for cmd, event in stream.escape.items():
        handler = counter()
        stream.connect(event, handler)

        stream.consume(ctrl.ESC)
        assert stream.state == "escape"
        assert not handler.count

        stream.consume(cmd)
        assert stream.state == "stream"
        assert handler.count == 1

    # ``linefeed``s is somewhat an exception, there's three ways to
    # trigger it.
    handler = counter()

    stream.connect("linefeed", handler)
    stream.feed(ctrl.LF + ctrl.VT + ctrl.FF)

    assert handler.count == 3
    assert stream.state == "stream"


def test_unknown_sequences():
    handler = argcheck()
    stream = TestStream()
    stream.connect("debug", handler)

    try:
        stream.feed(ctrl.CSI + "6;Z")
    except Exception as e:
        pytest.fail("No exception should've raised, got: %s" % e)
    else:
        assert handler.count == 1
        assert handler.args == (6, 0)
        assert handler.kwargs == {"unhandled": "Z", "state": "arguments"}


def test_non_csi_sequences():
    stream = TestStream()

    for cmd, event in stream.csi.items():
        # a) single param
        handler = argcheck()
        stream.connect(event, handler)
        stream.consume(ctrl.ESC)
        assert stream.state == "escape"

        stream.consume("[")
        assert stream.state == "arguments"

        stream.consume("5")
        stream.consume(cmd)

        assert handler.count == 1
        assert handler.args == (5, )
        assert stream.state == "stream"

        # b) multiple params, and starts with CSI, not ESC [
        handler = argcheck()
        stream.connect(event, handler)
        stream.consume(ctrl.CSI)
        assert stream.state == "arguments"

        stream.consume("5")
        stream.consume(";")
        stream.consume("12")
        stream.consume(cmd)

        assert handler.count == 1
        assert handler.args == (5, 12)
        assert stream.state == "stream"


def test_mode_csi_sequences():
    bugger = counter()
    stream = TestStream()
    stream.connect("debug", bugger)

    # a) set_mode
    handler = argcheck()
    stream.connect("set_mode", handler)
    stream.feed(ctrl.CSI + "?9;2h")

    assert not bugger.count
    assert handler.count == 1
    assert handler.args == (9, 2)
    assert handler.kwargs == {"private": True}

    # a) reset_mode
    handler = argcheck()
    stream.connect("reset_mode", handler)
    stream.feed(ctrl.CSI + "?9;2l")

    assert not bugger.count
    assert handler.count == 1
    assert handler.args == (9, 2)


def test_byte_stream():
    def validator(char):
        assert "\ufffd" not in char

    stream = TestByteStream(encodings=[("utf_8", "replace")])
    stream.connect("draw", validator)

    for byte in "Garðabær".encode("utf_8"):
        if sys.version_info[0] == 3:
            # HACK(Sergei): in Python 3 a _byte_ is just an `int``, while
            # in Python 2 it's an instance of `str``.
            byte = bytes([byte])

        stream.feed(byte)


def test_missing_params():
    handler = argcheck()
    stream = TestStream()
    stream.connect("cursor_position", handler)

    stream.feed(ctrl.CSI + ";" + esc.HVP)
    assert handler.count == 1
    assert handler.args == (0, 0)


def test_overflow():
    handler = argcheck()
    stream = TestStream()
    stream.connect("cursor_position", handler)

    stream.feed(ctrl.CSI + "999999999999999;99999999999999" + esc.HVP)
    assert handler.count == 1
    assert handler.args == (9999, 9999)


def test_interrupt():
    bugger, handler = argstore(), argcheck()
    stream = TestStream()
    stream.connect("draw", bugger)
    stream.connect("cursor_position", handler)

    stream.feed(ctrl.CSI + "10;" + ctrl.SUB + "10" + esc.HVP)

    assert not handler.count
    assert bugger.seen == [
        ctrl.SUB, "1", "0", esc.HVP
    ]


def test_control_characters():
    handler = argcheck()
    stream = TestStream()
    stream.connect("cursor_position", handler)

    stream.feed(ctrl.CSI + "10;\t\t\n\r\n10" + esc.HVP)

    assert handler.count == 1
    assert handler.args == (10, 10)

def test_debug_stream():
    tests = [
        (b"foo", "DRAW f\nDRAW o\nDRAW o"),
        (b"\x1b[1;24r\x1b[4l\x1b[24;1H",
         "SET_MARGINS 1; 24\nRESET_MODE 4\nCURSOR_POSITION 24; 1"),
    ]

    for input, expected in tests:
        output = StringIO()
        stream = DebugStream(to=output)
        stream.feed(input)

        lines = [l.rstrip() for l in output.getvalue().splitlines()]
        assert lines == expected.splitlines()
