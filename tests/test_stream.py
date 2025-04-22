import io

import pytest

import pyte
from pyte import charsets as cs, control as ctrl, escape as esc


class counter:
    def __init__(self):
        self.count = 0

    def __call__(self, *args, **kwargs):
        self.count += 1


class argcheck(counter):
    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        super().__call__()


class argstore:
    def __init__(self):
        self.seen = []

    def __call__(self, *args):
        self.seen.extend(args)


class IntentionalException(Exception):
    pass


def test_basic_sequences():
    for cmd, event in pyte.Stream.escape.items():
        screen = pyte.Screen(80, 24)
        handler = counter()
        setattr(screen, event, handler)

        stream = pyte.Stream(screen)
        stream.feed(ctrl.ESC)
        assert not handler.count

        stream.feed(cmd)
        assert handler.count == 1, event


def test_linefeed():
    # ``linefeed`` is somewhat an exception, there's three ways to
    # trigger it.
    handler = counter()
    screen = pyte.Screen(80, 24)
    screen.linefeed = handler

    stream = pyte.Stream(screen)
    stream.feed(ctrl.LF + ctrl.VT + ctrl.FF)
    assert handler.count == 3


def test_unknown_sequences():
    handler = argcheck()
    screen = pyte.Screen(80, 24)
    screen.debug = handler

    stream = pyte.Stream(screen)
    stream.feed(ctrl.CSI + "6;Z")
    assert handler.count == 1
    assert handler.args == (6, 0)
    assert handler.kwargs == {}


def test_non_csi_sequences():
    for cmd, event in pyte.Stream.csi.items():
        # a) single param
        handler = argcheck()
        screen = pyte.Screen(80, 24)
        setattr(screen, event, handler)

        stream = pyte.Stream(screen)
        stream.feed(ctrl.ESC + "[5" + cmd)
        assert handler.count == 1
        assert handler.args == (5, )

        # b) multiple params, and starts with CSI, not ESC [
        handler = argcheck()
        screen = pyte.Screen(80, 24)
        setattr(screen, event, handler)

        stream = pyte.Stream(screen)
        stream.feed(ctrl.CSI + "5;12" + cmd)
        assert handler.count == 1
        assert handler.args == (5, 12)


def test_set_mode():
    bugger = counter()
    screen = pyte.Screen(80, 24)
    handler = argcheck()
    screen.debug = bugger
    screen.set_mode = handler

    stream = pyte.Stream(screen)
    stream.feed(ctrl.CSI + "?9;2h")
    assert not bugger.count
    assert handler.count == 1
    assert handler.args == (9, 2)
    assert handler.kwargs == {"private": True}


def test_reset_mode():
    bugger = counter()
    screen = pyte.Screen(80, 24)
    handler = argcheck()
    screen.debug = bugger
    screen.reset_mode = handler

    stream = pyte.Stream(screen)
    stream.feed(ctrl.CSI + "?9;2l")
    assert not bugger.count
    assert handler.count == 1
    assert handler.args == (9, 2)


def test_missing_params():
    handler = argcheck()
    screen = pyte.Screen(80, 24)
    screen.cursor_position = handler

    stream = pyte.Stream(screen)
    stream.feed(ctrl.CSI + ";" + esc.HVP)
    assert handler.count == 1
    assert handler.args == (0, 0)


def test_overflow():
    handler = argcheck()
    screen = pyte.Screen(80, 24)
    screen.cursor_position = handler

    stream = pyte.Stream(screen)
    stream.feed(ctrl.CSI + "999999999999999;99999999999999" + esc.HVP)
    assert handler.count == 1
    assert handler.args == (9999, 9999)


def test_interrupt():
    bugger = argstore()
    handler = argcheck()

    screen = pyte.Screen(80, 24)
    screen.draw = bugger
    screen.cursor_position = handler

    stream = pyte.Stream(screen)
    stream.feed(ctrl.CSI + "10;" + ctrl.SUB + "10" + esc.HVP)

    assert not handler.count
    assert bugger.seen == [
        ctrl.SUB, "10" + esc.HVP
    ]


def test_control_characters():
    handler = argcheck()
    screen = pyte.Screen(80, 24)
    screen.cursor_position = handler

    stream = pyte.Stream(screen)
    stream.feed(ctrl.CSI + "10;\t\t\n\r\n10" + esc.HVP)

    assert handler.count == 1
    assert handler.args == (10, 10)


@pytest.mark.parametrize('osc,st', [
    (ctrl.OSC_C0, ctrl.ST_C0),
    (ctrl.OSC_C0, ctrl.ST_C1),
    (ctrl.OSC_C1, ctrl.ST_C0),
    (ctrl.OSC_C1, ctrl.ST_C1)
])
def test_set_title_icon_name(osc, st):
    screen = pyte.Screen(80, 24)
    stream = pyte.Stream(screen)

    # a) set only icon name
    stream.feed(osc + "1;foo" + st)
    assert screen.icon_name == "foo"

    # b) set only title
    stream.feed(osc + "2;foo" + st)
    assert screen.title == "foo"

    # c) set both icon name and title
    stream.feed(osc + "0;bar" + st)
    assert screen.title == screen.icon_name == "bar"

    # d) set both icon name and title then terminate with BEL
    stream.feed(osc + "0;bar" + st)
    assert screen.title == screen.icon_name == "bar"

    # e) test ➜ ('\xe2\x9e\x9c') symbol, that contains string terminator \x9c
    stream.feed("➜")
    assert screen.buffer[0][0].data == "➜"


def test_compatibility_api():
    screen = pyte.Screen(80, 24)
    stream = pyte.Stream()
    stream.attach(screen)

    # All of the following shouldn't raise errors.
    # a) adding more than one listener
    stream.attach(pyte.Screen(80, 24))

    # b) feeding text
    stream.feed("привет")

    # c) detaching an attached screen.
    stream.detach(screen)


def test_define_charset():
    # Should be a noop. All input is UTF8.
    screen = pyte.Screen(3, 3)
    stream = pyte.Stream(screen)
    stream.feed(ctrl.ESC + "(B")
    assert screen.display[0] == " " * 3


def test_non_utf8_shifts():
    screen = pyte.Screen(3, 3)
    handler = screen.shift_in = screen.shift_out = argcheck()
    stream = pyte.Stream(screen)
    stream.use_utf8 = False
    stream.feed(ctrl.SI)
    stream.feed(ctrl.SO)
    assert handler.count == 2


def test_dollar_skip():
    screen = pyte.Screen(3, 3)
    handler = screen.draw = argcheck()
    stream = pyte.Stream(screen)
    stream.feed(ctrl.CSI + "12$p")
    assert handler.count == 0
    stream.feed(ctrl.CSI + "1;2;3;4$x")
    assert handler.count == 0


@pytest.mark.parametrize("input,expected", [
    (b"foo", [["draw", ["foo"], {}]]),
    (b"\x1b[1;24r\x1b[4l\x1b[24;1H", [
        ["set_margins", [1, 24], {}],
        ["reset_mode", [4], {}],
        ["cursor_position", [24, 1], {}]])
])
def test_debug_stream(input, expected):
    output = io.StringIO()
    stream = pyte.ByteStream(pyte.DebugScreen(to=output))
    stream.feed(input)

    output.seek(0)
    assert [eval(line) for line in output] == expected


def test_handler_exception():
    # When an error occurs in a handler, the stream should continue to
    # work. See PR #101 for details.

    def failing_handler(*args, **kwargs):
        raise IntentionalException()

    handler = argcheck()
    screen = pyte.Screen(80, 24)
    screen.set_mode = failing_handler
    screen.reset_mode = handler

    stream = pyte.Stream(screen)
    with pytest.raises(IntentionalException):
        stream.feed(ctrl.CSI + "?9;2h")

    stream.feed(ctrl.CSI + "?9;2l")
    assert handler.count == 1


def test_byte_stream_feed():
    screen = pyte.Screen(20, 1)
    screen.draw = handler = argcheck()

    stream = pyte.ByteStream(screen)
    stream.feed("Нерусский текст".encode())
    assert handler.count == 1
    assert handler.args == ("Нерусский текст", )


def test_byte_stream_define_charset_unknown():
    screen = pyte.Screen(3, 3)
    stream = pyte.ByteStream(screen)
    stream.select_other_charset("@")
    default_g0_charset = screen.g0_charset
    # ``"Z"`` is not supported by Linux terminal, so expect a noop.
    assert "Z" not in cs.MAPS
    stream.feed((ctrl.ESC + "(Z").encode())
    assert screen.display[0] == " " * 3
    assert screen.g0_charset == default_g0_charset


@pytest.mark.parametrize("charset,mapping", cs.MAPS.items())
def test_byte_stream_define_charset(charset, mapping):
    screen = pyte.Screen(3, 3)
    stream = pyte.ByteStream(screen)
    stream.select_other_charset("@")
    stream.feed((ctrl.ESC + "(" + charset).encode())
    assert screen.display[0] == " " * 3
    assert screen.g0_charset == mapping


def test_byte_stream_select_other_charset():
    stream = pyte.ByteStream(pyte.Screen(3, 3))
    assert stream.use_utf8  # on by default.

    # a) disable utf-8
    stream.select_other_charset("@")
    assert not stream.use_utf8

    # b) unknown code -- noop
    stream.select_other_charset("X")
    assert not stream.use_utf8

    # c) enable utf-8
    stream.select_other_charset("G")
    assert stream.use_utf8
