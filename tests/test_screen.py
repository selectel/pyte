import copy

import pytest

import pyte
from pyte import modes as mo, control as ctrl, graphics as g
from pyte.screens import Char


# Test helpers.

def update(screen, lines, colored=[]):
    """Updates a given screen object with given lines, colors each line
    from ``colored`` in "red" and returns the modified screen.
    """
    for y, line in enumerate(lines):
        for x, char in enumerate(line):
            if y in colored:
                attrs = {"fg": "red"}
            else:
                attrs = {}
            screen.buffer[y][x] = Char(data=char, **attrs)

    return screen


def tolist(screen):
    return [[screen.buffer[y][x] for x in range(screen.columns)]
            for y in range(screen.lines)]


# Tests.

def test_initialize_char():
    # Make sure that char can be correctly initialized with keyword
    # arguments. See #24 on GitHub for details.
    for field in Char._fields[1:]:
        char = Char(field[0], **{field: True})
        assert getattr(char, field)


def test_remove_non_existant_attribute():
    screen = pyte.Screen(2, 2)
    assert tolist(screen) == [[screen.default_char, screen.default_char]] * 2

    screen.select_graphic_rendition(24)  # underline-off.
    assert tolist(screen) == [[screen.default_char, screen.default_char]] * 2
    assert not screen.cursor.attrs.underscore


def test_attributes():
    screen = pyte.Screen(2, 2)
    assert tolist(screen) == [[screen.default_char, screen.default_char]] * 2
    screen.select_graphic_rendition(1)  # bold.

    # Still default, since we haven't written anything.
    assert tolist(screen) == [[screen.default_char, screen.default_char]] * 2
    assert screen.cursor.attrs.bold

    screen.draw("f")
    assert tolist(screen) == [
        [Char("f", "default", "default", bold=True), screen.default_char],
        [screen.default_char, screen.default_char]
    ]


def test_blink():
    screen = pyte.Screen(2, 2)
    assert tolist(screen) == [[screen.default_char, screen.default_char]] * 2
    screen.select_graphic_rendition(5)  # blink.

    screen.draw("f")
    assert tolist(screen) == [
        [Char("f", "default", "default", blink=True), screen.default_char],
        [screen.default_char, screen.default_char]
    ]


def test_colors():
    screen = pyte.Screen(2, 2)

    screen.select_graphic_rendition(30)
    screen.select_graphic_rendition(40)
    assert screen.cursor.attrs.fg == "black"
    assert screen.cursor.attrs.bg == "black"

    screen.select_graphic_rendition(31)
    assert screen.cursor.attrs.fg == "red"
    assert screen.cursor.attrs.bg == "black"


def test_colors256():
    screen = pyte.Screen(2, 2)

    # a) OK-case.
    screen.select_graphic_rendition(g.FG_256, 5, 0)
    screen.select_graphic_rendition(g.BG_256, 5, 15)
    assert screen.cursor.attrs.fg == "000000"
    assert screen.cursor.attrs.bg == "ffffff"

    # b) invalid color.
    screen.select_graphic_rendition(48, 5, 100500)


def test_colors256_missing_attrs():
    # Test from https://github.com/selectel/pyte/issues/115
    screen = pyte.Screen(2, 2)
    screen.select_graphic_rendition(g.FG_256)
    screen.select_graphic_rendition(g.BG_256)
    assert screen.cursor.attrs == screen.default_char


def test_colors24bit():
    screen = pyte.Screen(2, 2)

    # a) OK-case
    screen.select_graphic_rendition(38, 2, 0, 0, 0)
    screen.select_graphic_rendition(48, 2, 255, 255, 255)
    assert screen.cursor.attrs.fg == "000000"
    assert screen.cursor.attrs.bg == "ffffff"

    # b) invalid color.
    screen.select_graphic_rendition(48, 2, 255)


def test_colors_aixterm():
    # See issue #57 on GitHub.
    screen = pyte.Screen(2, 2)

    # a) foreground color.
    screen.select_graphic_rendition(94)
    assert screen.cursor.attrs.fg == "brightblue"

    # b) background color.
    screen.select_graphic_rendition(104)
    assert screen.cursor.attrs.bg == "brightblue"


def test_colors_ignore_invalid():
    screen = pyte.Screen(2, 2)
    default_attrs = screen.cursor.attrs

    screen.select_graphic_rendition(100500)
    assert screen.cursor.attrs == default_attrs

    screen.select_graphic_rendition(38, 100500)
    assert screen.cursor.attrs == default_attrs

    screen.select_graphic_rendition(48, 100500)
    assert screen.cursor.attrs == default_attrs


def test_reset_resets_colors():
    screen = pyte.Screen(2, 2)
    assert tolist(screen) == [[screen.default_char, screen.default_char]] * 2

    screen.select_graphic_rendition(30)
    screen.select_graphic_rendition(40)
    assert screen.cursor.attrs.fg == "black"
    assert screen.cursor.attrs.bg == "black"

    screen.select_graphic_rendition(0)
    assert screen.cursor.attrs == screen.default_char


def test_reset_works_between_attributes():
    screen = pyte.Screen(2, 2)
    assert tolist(screen) == [[screen.default_char, screen.default_char]] * 2

    # Red fg, reset, red bg
    screen.select_graphic_rendition(31, 0, 41)
    assert screen.cursor.attrs.fg == "default"
    assert screen.cursor.attrs.bg == "red"


def test_multi_attribs():
    screen = pyte.Screen(2, 2)
    assert tolist(screen) == [[screen.default_char, screen.default_char]] * 2
    screen.select_graphic_rendition(1)
    screen.select_graphic_rendition(3)

    assert screen.cursor.attrs.bold
    assert screen.cursor.attrs.italics


def test_attributes_reset():
    screen = pyte.Screen(2, 2)
    screen.set_mode(mo.LNM)
    assert tolist(screen) == [[screen.default_char, screen.default_char]] * 2
    screen.select_graphic_rendition(1)
    screen.draw("f")
    screen.draw("o")
    screen.draw("o")
    assert tolist(screen) == [
        [Char("f", bold=True), Char("o", bold=True)],
        [Char("o", bold=True), screen.default_char],
    ]

    screen.cursor_position()
    screen.select_graphic_rendition(0)  # Reset
    screen.draw("f")
    assert tolist(screen) == [
        [Char("f"), Char("o", bold=True)],
        [Char("o", bold=True), screen.default_char],
    ]


def test_resize():
    screen = pyte.Screen(2, 2)
    screen.set_mode(mo.DECOM)
    screen.set_margins(0, 1)
    assert screen.columns == screen.lines == 2
    assert tolist(screen) == [[screen.default_char, screen.default_char]] * 2

    screen.resize(3, 3)
    assert screen.columns == screen.lines == 3
    assert tolist(screen) == [
        [screen.default_char, screen.default_char, screen.default_char]
    ] * 3
    assert mo.DECOM in screen.mode
    assert screen.margins is None

    screen.resize(2, 2)
    assert screen.columns == screen.lines == 2
    assert tolist(screen) == [[screen.default_char, screen.default_char]] * 2

    # Quirks:
    # a) if the current display is narrower than the requested size,
    #    new columns should be added to the right.
    screen = update(pyte.Screen(2, 2), ["bo", "sh"], [None, None])
    screen.resize(2, 3)
    assert screen.display == ["bo ", "sh "]

    # b) if the current display is wider than the requested size,
    #    columns should be removed from the right...
    screen = update(pyte.Screen(2, 2), ["bo", "sh"], [None, None])
    screen.resize(2, 1)
    assert screen.display == ["b", "s"]

    # c) if the current display is shorter than the requested
    #    size, new rows should be added on the bottom.
    screen = update(pyte.Screen(2, 2), ["bo", "sh"], [None, None])
    screen.resize(3, 2)

    assert screen.display == ["bo", "sh", "  "]

    # d) if the current display is taller than the requested
    #    size, rows should be removed from the top.
    screen = update(pyte.Screen(2, 2), ["bo", "sh"], [None, None])
    screen.resize(1, 2)
    assert screen.display == ["sh"]


def test_resize_same():
    screen = pyte.Screen(2, 2)
    screen.dirty.clear()
    screen.resize(2, 2)
    assert not screen.dirty


def test_set_mode():
    # Test mo.DECCOLM mode
    screen = update(pyte.Screen(3, 3), ["sam", "is ", "foo"])
    screen.cursor_position(1, 1)
    screen.set_mode(mo.DECCOLM)
    for line in range(3):
        for char in tolist(screen)[line]:
            assert char == screen.default_char
    assert screen.columns == 132
    assert screen.cursor.x == 0
    assert screen.cursor.y == 0
    screen.reset_mode(mo.DECCOLM)
    assert screen.columns == 3

    # Test mo.DECOM mode
    screen = update(pyte.Screen(3, 3), ["sam", "is ", "foo"])
    screen.cursor_position(1, 1)
    screen.set_mode(mo.DECOM)
    assert screen.cursor.x == 0
    assert screen.cursor.y == 0

    # Test mo.DECSCNM mode
    screen = update(pyte.Screen(3, 3), ["sam", "is ", "foo"])
    screen.set_mode(mo.DECSCNM)
    for line in range(3):
        for char in tolist(screen)[line]:
            assert char.reverse
    assert screen.default_char.reverse
    screen.reset_mode(mo.DECSCNM)
    for line in range(3):
        for char in tolist(screen)[line]:
            assert not char.reverse
    assert not screen.default_char.reverse

    # Test mo.DECTCEM mode
    screen = update(pyte.Screen(3, 3), ["sam", "is ", "foo"])
    screen.cursor.hidden = True
    screen.set_mode(mo.DECTCEM)
    assert not screen.cursor.hidden
    screen.reset_mode(mo.DECTCEM)
    assert screen.cursor.hidden


def test_draw():
    # ``DECAWM`` on (default).
    screen = pyte.Screen(3, 3)
    screen.set_mode(mo.LNM)
    assert mo.DECAWM in screen.mode

    for ch in "abc":
        screen.draw(ch)

    assert screen.display == ["abc", "   ", "   "]
    assert (screen.cursor.y, screen.cursor.x) == (0, 3)

    # ... one` more character -- now we got a linefeed!
    screen.draw("a")
    assert (screen.cursor.y, screen.cursor.x) == (1, 1)

    # ``DECAWM`` is off.
    screen = pyte.Screen(3, 3)
    screen.reset_mode(mo.DECAWM)

    for ch in "abc":
        screen.draw(ch)

    assert screen.display == ["abc", "   ", "   "]
    assert (screen.cursor.y, screen.cursor.x) == (0, 3)

    # No linefeed is issued on the end of the line ...
    screen.draw("a")
    assert screen.display == ["aba", "   ", "   "]
    assert (screen.cursor.y, screen.cursor.x) == (0, 3)

    # ``IRM`` mode is on, expecting new characters to move the old ones
    # instead of replacing them.
    screen.set_mode(mo.IRM)
    screen.cursor_position()
    screen.draw("x")
    assert screen.display == ["xab", "   ", "   "]

    screen.cursor_position()
    screen.draw("y")
    assert screen.display == ["yxa", "   ", "   "]


def test_draw_russian():
    # Test from https://github.com/selectel/pyte/issues/65
    screen = pyte.Screen(20, 1)
    stream = pyte.Stream(screen)
    stream.feed("Нерусский текст")
    assert screen.display == ["Нерусский текст     "]


def test_draw_multiple_chars():
    screen = pyte.Screen(10, 1)
    screen.draw("foobar")
    assert screen.cursor.x == 6
    assert screen.display == ["foobar    "]


def test_draw_utf8():
    # See https://github.com/selectel/pyte/issues/62
    screen = pyte.Screen(1, 1)
    stream = pyte.ByteStream(screen)
    stream.feed(b"\xE2\x80\x9D")
    assert screen.display == ["”"]


def test_draw_width2():
    # Example from https://github.com/selectel/pyte/issues/9
    screen = pyte.Screen(10, 1)
    screen.draw("コンニチハ")
    assert screen.cursor.x == screen.columns


def test_draw_width2_line_end():
    # Test from https://github.com/selectel/pyte/issues/55
    screen = pyte.Screen(10, 1)
    screen.draw(" コンニチハ")
    assert screen.cursor.x == screen.columns


@pytest.mark.xfail
def test_draw_width2_irm():
    screen = pyte.Screen(2, 1)
    screen.draw("コ")
    assert screen.display == ["コ"]
    assert tolist(screen) == [[Char("コ"), Char(" ")]]

    # Overwrite the stub part of a width 2 character.
    screen.set_mode(mo.IRM)
    screen.cursor_to_column(screen.columns)
    screen.draw("x")
    assert screen.display == [" x"]


def test_draw_width0_combining():
    screen = pyte.Screen(4, 2)

    # a) no prev. character
    screen.draw("\N{COMBINING DIAERESIS}")
    assert screen.display == ["    ", "    "]

    screen.draw("bad")

    # b) prev. character is on the same line
    screen.draw("\N{COMBINING DIAERESIS}")
    assert screen.display == ["bad̈ ", "    "]

    # c) prev. character is on the prev. line
    screen.draw("!")
    screen.draw("\N{COMBINING DIAERESIS}")
    assert screen.display == ["bad̈!̈", "    "]


def test_draw_width0_irm():
    screen = pyte.Screen(10, 1)
    screen.set_mode(mo.IRM)

    # The following should not insert any blanks.
    screen.draw("\N{ZERO WIDTH SPACE}")
    screen.draw("\u0007")  # DELETE.
    assert screen.display == [" " * screen.columns]


def test_draw_width0_decawm_off():
    screen = pyte.Screen(10, 1)
    screen.reset_mode(mo.DECAWM)
    screen.draw(" コンニチハ")
    assert screen.cursor.x == screen.columns

    # The following should not advance the cursor.
    screen.draw("\N{ZERO WIDTH SPACE}")
    screen.draw("\u0007")  # DELETE.
    assert screen.cursor.x == screen.columns


def test_draw_cp437():
    screen = pyte.Screen(5, 1)
    stream = pyte.ByteStream(screen)
    assert screen.charset == 0

    screen.define_charset("U", "(")
    stream.select_other_charset("@")
    stream.feed("α ± ε".encode("cp437"))

    assert screen.display == ["α ± ε"]


def test_draw_with_carriage_return():
    # See https://github.com/selectel/pyte/issues/66
    line = """\
ipcs -s | grep nobody |awk '{print$2}'|xargs -n1 i\
pcrm sem ;ps aux|grep -P 'httpd|fcgi'|grep -v grep\
|awk '{print$2 \x0D}'|xargs kill -9;/etc/init.d/ht\
tpd startssl"""

    screen = pyte.Screen(50, 3)
    stream = pyte.Stream(screen)
    stream.feed(line)

    assert screen.display == [
        "ipcs -s | grep nobody |awk '{print$2}'|xargs -n1 i",
        "pcrm sem ;ps aux|grep -P 'httpd|fcgi'|grep -v grep",
        "}'|xargs kill -9;/etc/init.d/httpd startssl       "
    ]


def test_display_wcwidth():
    screen = pyte.Screen(10, 1)
    screen.draw("コンニチハ")
    assert screen.display == ["コンニチハ"]


def test_display_multi_char_emoji():
    screen = pyte.Screen(4, 1)
    screen.draw("👨\u200d💻a")
    assert screen.display == ["👨\u200d💻a "]


def test_display_complex_emoji():
    emoji = "\U0001f926\U0001f3fd\u200d\u2642\ufe0f"
    screen = pyte.Screen(4, 1)
    screen.draw(emoji + "a")
    assert screen.display == [emoji + "a "]


def test_carriage_return():
    screen = pyte.Screen(3, 3)
    screen.cursor.x = 2
    screen.carriage_return()

    assert screen.cursor.x == 0


def test_index():
    screen = update(pyte.Screen(2, 2), ["wo", "ot"], colored=[1])

    # a) indexing on a row that isn't the last should just move
    # the cursor down.
    screen.index()
    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert tolist(screen) == [
        [Char("w"), Char("o")],
        [Char("o", fg="red"), Char("t", fg="red")]
    ]

    # b) indexing on the last row should push everything up and
    # create a new row at the bottom.
    screen.index()
    assert screen.cursor.y == 1
    assert tolist(screen) == [
        [Char("o", fg="red"), Char("t", fg="red")],
        [screen.default_char, screen.default_char]
    ]

    # c) same with margins
    screen = update(pyte.Screen(2, 5), ["bo", "sh", "th", "er", "oh"],
                    colored=[1, 2])
    screen.set_margins(2, 4)
    screen.cursor.y = 3

    # ... go!
    screen.index()
    assert (screen.cursor.y, screen.cursor.x) == (3, 0)
    assert screen.display == ["bo", "th", "er", "  ", "oh"]
    assert tolist(screen) == [
        [Char("b"), Char("o", "default")],
        [Char("t", "red"), Char("h", "red")],
        [Char("e"), Char("r")],
        [screen.default_char, screen.default_char],
        [Char("o"), Char("h")],
    ]

    # ... and again ...
    screen.index()
    assert (screen.cursor.y, screen.cursor.x) == (3, 0)
    assert screen.display == ["bo", "er", "  ", "  ", "oh"]
    assert tolist(screen) == [
        [Char("b"), Char("o")],
        [Char("e"), Char("r")],
        [screen.default_char, screen.default_char],
        [screen.default_char, screen.default_char],
        [Char("o"), Char("h")],
    ]

    # ... and again ...
    screen.index()
    assert (screen.cursor.y, screen.cursor.x) == (3, 0)
    assert screen.display == ["bo", "  ", "  ", "  ", "oh"]
    assert tolist(screen) == [
        [Char("b"), Char("o")],
        [screen.default_char, screen.default_char],
        [screen.default_char, screen.default_char],
        [screen.default_char, screen.default_char],
        [Char("o"), Char("h")],
    ]

    # look, nothing changes!
    screen.index()
    assert (screen.cursor.y, screen.cursor.x) == (3, 0)
    assert screen.display == ["bo", "  ", "  ", "  ", "oh"]
    assert tolist(screen) == [
        [Char("b"), Char("o")],
        [screen.default_char, screen.default_char],
        [screen.default_char, screen.default_char],
        [screen.default_char, screen.default_char],
        [Char("o"), Char("h")],
    ]


def test_reverse_index():
    screen = update(pyte.Screen(2, 2), ["wo", "ot"], colored=[0])

    # a) reverse indexing on the first row should push rows down
    # and create a new row at the top.
    screen.reverse_index()
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert tolist(screen) == [
        [screen.default_char, screen.default_char],
        [Char("w", fg="red"), Char("o", fg="red")]
    ]

    # b) once again ...
    screen.reverse_index()
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert tolist(screen) == [
        [screen.default_char, screen.default_char],
        [screen.default_char, screen.default_char],
    ]

    # c) same with margins
    screen = update(pyte.Screen(2, 5), ["bo", "sh", "th", "er", "oh"],
                    colored=[2, 3])
    screen.set_margins(2, 4)
    screen.cursor.y = 1

    # ... go!
    screen.reverse_index()
    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["bo", "  ", "sh", "th", "oh"]
    assert tolist(screen) == [
        [Char("b"), Char("o")],
        [screen.default_char, screen.default_char],
        [Char("s"), Char("h")],
        [Char("t", fg="red"), Char("h", fg="red")],
        [Char("o"), Char("h")],
    ]

    # ... and again ...
    screen.reverse_index()
    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["bo", "  ", "  ", "sh", "oh"]
    assert tolist(screen) == [
        [Char("b"), Char("o")],
        [screen.default_char, screen.default_char],
        [screen.default_char, screen.default_char],
        [Char("s"), Char("h")],
        [Char("o"), Char("h")],
    ]

    # ... and again ...
    screen.reverse_index()
    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["bo", "  ", "  ", "  ", "oh"]
    assert tolist(screen) == [
        [Char("b"), Char("o")],
        [screen.default_char, screen.default_char],
        [screen.default_char, screen.default_char],
        [screen.default_char, screen.default_char],
        [Char("o"), Char("h")],
    ]

    # look, nothing changes!
    screen.reverse_index()
    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["bo", "  ", "  ", "  ", "oh"]
    assert tolist(screen) == [
        [Char("b"), Char("o")],
        [screen.default_char, screen.default_char],
        [screen.default_char, screen.default_char],
        [screen.default_char, screen.default_char],
        [Char("o"), Char("h")],
    ]


def test_linefeed():
    screen = update(pyte.Screen(2, 2), ["bo", "sh"], [None, None])
    screen.set_mode(mo.LNM)

    # a) LNM on by default (that's what `vttest` forces us to do).
    assert mo.LNM in screen.mode
    screen.cursor.x, screen.cursor.y = 1, 0
    screen.linefeed()
    assert (screen.cursor.y, screen.cursor.x) == (1, 0)

    # b) LNM off.
    screen.reset_mode(mo.LNM)
    screen.cursor.x, screen.cursor.y = 1, 0
    screen.linefeed()
    assert (screen.cursor.y, screen.cursor.x) == (1, 1)


def test_linefeed_margins():
    # See issue #63 on GitHub.
    screen = pyte.Screen(80, 24)
    screen.set_margins(3, 27)
    screen.cursor_position()
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    screen.linefeed()
    assert (screen.cursor.y, screen.cursor.x) == (1, 0)


def test_tabstops():
    screen = pyte.Screen(10, 10)

    # Making sure initial tabstops are in place ...
    assert screen.tabstops == {8}

    # ... and clearing them.
    screen.clear_tab_stop(3)
    assert not screen.tabstops

    screen.cursor.x = 1
    screen.set_tab_stop()
    screen.cursor.x = 8
    screen.set_tab_stop()

    screen.cursor.x = 0
    screen.tab()
    assert screen.cursor.x == 1
    screen.tab()
    assert screen.cursor.x == 8
    screen.tab()
    assert screen.cursor.x == 9
    screen.tab()
    assert screen.cursor.x == 9


def test_clear_tabstops():
    screen = pyte.Screen(10, 10)
    screen.clear_tab_stop(3)

    # a) clear a tabstop at current cursor location
    screen.cursor.x = 1
    screen.set_tab_stop()
    screen.cursor.x = 5
    screen.set_tab_stop()
    screen.clear_tab_stop()

    assert screen.tabstops == {1}

    screen.set_tab_stop()
    screen.clear_tab_stop(0)

    assert screen.tabstops == {1}

    # b) all tabstops
    screen.set_tab_stop()
    screen.cursor.x = 9
    screen.set_tab_stop()
    screen.clear_tab_stop(3)

    assert not screen.tabstops


def test_backspace():
    screen = pyte.Screen(2, 2)
    assert screen.cursor.x == 0
    screen.backspace()
    assert screen.cursor.x == 0
    screen.cursor.x = 1
    screen.backspace()
    assert screen.cursor.x == 0


def test_save_cursor():
    # a) cursor position
    screen = pyte.Screen(10, 10)
    screen.save_cursor()
    screen.cursor.x, screen.cursor.y = 3, 5
    screen.save_cursor()
    screen.cursor.x, screen.cursor.y = 4, 4

    screen.restore_cursor()
    assert screen.cursor.x == 3
    assert screen.cursor.y == 5

    screen.restore_cursor()
    assert screen.cursor.x == 0
    assert screen.cursor.y == 0

    # b) modes
    screen = pyte.Screen(10, 10)
    screen.set_mode(mo.DECAWM, mo.DECOM)
    screen.save_cursor()

    screen.reset_mode(mo.DECAWM)

    screen.restore_cursor()
    assert mo.DECAWM in screen.mode
    assert mo.DECOM in screen.mode

    # c) attributes
    screen = pyte.Screen(10, 10)
    screen.select_graphic_rendition(4)
    screen.save_cursor()
    screen.select_graphic_rendition(24)

    assert screen.cursor.attrs == screen.default_char

    screen.restore_cursor()

    assert screen.cursor.attrs != screen.default_char
    assert screen.cursor.attrs == Char(" ", underscore=True)


def test_restore_cursor_with_none_saved():
    screen = pyte.Screen(10, 10)
    screen.set_mode(mo.DECOM)
    screen.cursor.x, screen.cursor.y = 5, 5
    screen.restore_cursor()

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert mo.DECOM not in screen.mode


def test_restore_cursor_out_of_bounds():
    screen = pyte.Screen(10, 10)

    # a) origin mode off.
    screen.cursor_position(5, 5)
    screen.save_cursor()
    screen.resize(3, 3)
    screen.reset()
    screen.restore_cursor()

    assert (screen.cursor.y, screen.cursor.x) == (2, 2)

    # b) origin mode is on.
    screen.resize(10, 10)
    screen.cursor_position(8, 8)
    screen.save_cursor()
    screen.resize(5, 5)
    screen.reset()
    screen.set_mode(mo.DECOM)
    screen.set_margins(2, 3)
    screen.restore_cursor()

    assert (screen.cursor.y, screen.cursor.x) == (2, 4)


def test_insert_lines():
    # a) without margins
    screen = update(pyte.Screen(3, 3), ["sam", "is ", "foo"], colored=[1])
    screen.insert_lines()

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["   ", "sam", "is "]
    assert tolist(screen) == [
        [screen.default_char] * 3,
        [Char("s"), Char("a"), Char("m")],
        [Char("i", fg="red"), Char("s", fg="red"), Char(" ", fg="red")],
    ]

    screen = update(pyte.Screen(3, 3), ["sam", "is ", "foo"], colored=[1])
    screen.insert_lines(2)

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["   ", "   ", "sam"]
    assert tolist(screen) == [
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [Char("s"), Char("a"), Char("m")]
    ]

    # b) with margins
    screen = update(pyte.Screen(3, 5), ["sam", "is ", "foo", "bar", "baz"],
                    colored=[2, 3])
    screen.set_margins(1, 4)
    screen.cursor.y = 1
    screen.insert_lines(1)

    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["sam", "   ", "is ", "foo", "baz"]
    assert tolist(screen) == [
        [Char("s"), Char("a"), Char("m")],
        [screen.default_char] * 3,
        [Char("i"), Char("s"), Char(" ")],
        [Char("f", fg="red"), Char("o", fg="red"), Char("o", fg="red")],
        [Char("b"), Char("a"), Char("z")],
    ]

    screen = update(pyte.Screen(3, 5), ["sam", "is ", "foo", "bar", "baz"],
                    colored=[2, 3])
    screen.set_margins(1, 3)
    screen.cursor.y = 1
    screen.insert_lines(1)

    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["sam", "   ", "is ", "bar",  "baz"]
    assert tolist(screen) == [
        [Char("s"), Char("a"), Char("m")],
        [screen.default_char] * 3,
        [Char("i"), Char("s"), Char(" ")],
        [Char("b", fg="red"), Char("a", fg="red"), Char("r", fg="red")],
        [Char("b"), Char("a"), Char("z")],
    ]

    screen.insert_lines(2)
    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["sam", "   ", "   ", "bar",  "baz"]
    assert tolist(screen) == [
        [Char("s"), Char("a"), Char("m")],
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [Char("b", fg="red"), Char("a", fg="red"), Char("r", fg="red")],
        [Char("b"), Char("a"), Char("z")],
    ]

    # c) with margins -- trying to insert more than we have available
    screen = update(pyte.Screen(3, 5), ["sam", "is ", "foo", "bar", "baz"],
                    colored=[2, 3])
    screen.set_margins(2, 4)
    screen.cursor.y = 1
    screen.insert_lines(20)

    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["sam", "   ", "   ", "   ", "baz"]
    assert tolist(screen) == [
        [Char("s"), Char("a"), Char("m")],
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [Char("b"), Char("a"), Char("z")],
    ]

    # d) with margins -- trying to insert outside scroll boundaries;
    #    expecting nothing to change
    screen = update(pyte.Screen(3, 5), ["sam", "is ", "foo", "bar", "baz"],
                    colored=[2, 3])
    screen.set_margins(2, 4)
    screen.insert_lines(5)

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["sam", "is ", "foo", "bar", "baz"]
    assert tolist(screen) == [
        [Char("s"), Char("a"), Char("m")],
        [Char("i"), Char("s"), Char(" ")],
        [Char("f", fg="red"), Char("o", fg="red"), Char("o", fg="red")],
        [Char("b", fg="red"), Char("a", fg="red"), Char("r", fg="red")],
        [Char("b"), Char("a"), Char("z")],
    ]


def test_delete_lines():
    # a) without margins
    screen = update(pyte.Screen(3, 3), ["sam", "is ", "foo"], colored=[1])
    screen.delete_lines()

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["is ", "foo", "   "]
    assert tolist(screen) == [
        [Char("i", fg="red"), Char("s", fg="red"), Char(" ", fg="red")],
        [Char("f"), Char("o"), Char("o")],
        [screen.default_char] * 3,
    ]

    screen.delete_lines(0)

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["foo", "   ", "   "]
    assert tolist(screen) == [
        [Char("f"), Char("o"), Char("o")],
        [screen.default_char] * 3,
        [screen.default_char] * 3,
    ]

    # b) with margins
    screen = update(pyte.Screen(3, 5), ["sam", "is ", "foo", "bar", "baz"],
                    colored=[2, 3])
    screen.set_margins(1, 4)
    screen.cursor.y = 1
    screen.delete_lines(1)

    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["sam", "foo", "bar", "   ", "baz"]
    assert tolist(screen) == [
        [Char("s"), Char("a"), Char("m")],
        [Char("f", fg="red"), Char("o", fg="red"), Char("o", fg="red")],
        [Char("b", fg="red"), Char("a", fg="red"), Char("r", fg="red")],
        [screen.default_char] * 3,
        [Char("b"), Char("a"), Char("z")],
    ]

    screen = update(pyte.Screen(3, 5), ["sam", "is ", "foo", "bar", "baz"],
                    colored=[2, 3])
    screen.set_margins(1, 4)
    screen.cursor.y = 1
    screen.delete_lines(2)

    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["sam", "bar", "   ", "   ", "baz"]
    assert tolist(screen) == [
        [Char("s"), Char("a"), Char("m")],
        [Char("b", fg="red"), Char("a", fg="red"), Char("r", fg="red")],
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [Char("b"), Char("a"), Char("z")],
    ]

    # c) with margins -- trying to delete  more than we have available
    screen = update(pyte.Screen(3, 5),
                    ["sam", "is ", "foo", "bar", "baz"],
                    [None,
                     None,
                     [("red", "default")] * 3,
                     [("red", "default")] * 3,
                     None])
    screen.set_margins(1, 4)
    screen.cursor.y = 1
    screen.delete_lines(5)

    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["sam", "   ", "   ", "   ", "baz"]
    assert tolist(screen) == [
        [Char("s"), Char("a"), Char("m")],
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [Char("b"), Char("a"), Char("z")],
    ]

    # d) with margins -- trying to delete outside scroll boundaries;
    #    expecting nothing to change
    screen = update(pyte.Screen(3, 5), ["sam", "is ", "foo", "bar", "baz"],
                    colored=[2, 3])
    screen.set_margins(2, 4)
    screen.cursor.y = 0
    screen.delete_lines(5)

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["sam", "is ", "foo", "bar", "baz"]
    assert tolist(screen) == [
        [Char("s"), Char("a"), Char("m")],
        [Char("i"), Char("s"), Char(" ")],
        [Char("f", fg="red"), Char("o", fg="red"), Char("o", fg="red")],
        [Char("b", fg="red"), Char("a", fg="red"), Char("r", fg="red")],
        [Char("b"), Char("a"), Char("z")],
    ]


def test_insert_characters():
    screen = update(pyte.Screen(3, 4), ["sam", "is ", "foo", "bar"],
                    colored=[0])

    # a) normal case
    cursor = copy.copy(screen.cursor)
    screen.insert_characters(2)
    assert (screen.cursor.y, screen.cursor.x) == (cursor.y, cursor.x)
    assert tolist(screen)[0] == [
        screen.default_char,
        screen.default_char,
        Char("s", fg="red")
    ]

    # b) now inserting from the middle of the line
    screen.cursor.y, screen.cursor.x = 2, 1
    screen.insert_characters(1)
    assert tolist(screen)[2] == [Char("f"), screen.default_char, Char("o")]

    # c) inserting more than we have
    screen.cursor.y, screen.cursor.x = 3, 1
    screen.insert_characters(10)
    assert tolist(screen)[3] == [
        Char("b"), screen.default_char, screen.default_char
    ]

    # d) 0 is 1
    screen = update(pyte.Screen(3, 3), ["sam", "is ", "foo"], colored=[0])

    screen.cursor_position()
    screen.insert_characters()
    assert tolist(screen)[0] == [
        screen.default_char,
        Char("s", fg="red"), Char("a", fg="red")
    ]

    screen = update(pyte.Screen(3, 3), ["sam", "is ", "foo"], colored=[0])
    screen.cursor_position()
    screen.insert_characters(1)
    assert tolist(screen)[0] == [
        screen.default_char,
        Char("s", fg="red"), Char("a", fg="red")
    ]


def test_delete_characters():
    screen = update(pyte.Screen(3, 3), ["sam", "is ", "foo"], colored=[0])
    screen.delete_characters(2)
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["m  ", "is ", "foo"]
    assert tolist(screen)[0] == [
        Char("m", fg="red"),
        screen.default_char, screen.default_char
    ]

    screen.cursor.y, screen.cursor.x = 2, 2
    screen.delete_characters()
    assert (screen.cursor.y, screen.cursor.x) == (2, 2)
    assert screen.display == ["m  ", "is ", "fo "]

    screen.cursor.y, screen.cursor.x = 1, 1
    screen.delete_characters(0)
    assert (screen.cursor.y, screen.cursor.x) == (1, 1)
    assert screen.display == ["m  ", "i  ", "fo "]

    # ! extreme cases.
    screen = update(pyte.Screen(5, 1), ["12345"], colored=[0])
    screen.cursor.x = 1
    screen.delete_characters(3)
    assert (screen.cursor.y, screen.cursor.x) == (0, 1)
    assert screen.display == ["15   "]
    assert tolist(screen)[0] == [
        Char("1", fg="red"),
        Char("5", fg="red"),
        screen.default_char,
        screen.default_char,
        screen.default_char
    ]

    screen = update(pyte.Screen(5, 1), ["12345"], colored=[0])
    screen.cursor.x = 2
    screen.delete_characters(10)
    assert (screen.cursor.y, screen.cursor.x) == (0, 2)
    assert screen.display == ["12   "]
    assert tolist(screen)[0] == [
        Char("1", fg="red"),
        Char("2", fg="red"),
        screen.default_char,
        screen.default_char,
        screen.default_char
    ]

    screen = update(pyte.Screen(5, 1), ["12345"], colored=[0])
    screen.delete_characters(4)
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["5    "]
    assert tolist(screen)[0] == [
        Char("5", fg="red"),
        screen.default_char,
        screen.default_char,
        screen.default_char,
        screen.default_char
    ]


def test_erase_character():
    screen = update(pyte.Screen(3, 3), ["sam", "is ", "foo"], colored=[0])

    screen.erase_characters(2)
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["  m", "is ", "foo"]
    assert tolist(screen)[0] == [
        screen.default_char,
        screen.default_char,
        Char("m", fg="red")
    ]

    screen.cursor.y, screen.cursor.x = 2, 2
    screen.erase_characters()
    assert (screen.cursor.y, screen.cursor.x) == (2, 2)
    assert screen.display == ["  m", "is ", "fo "]

    screen.cursor.y, screen.cursor.x = 1, 1
    screen.erase_characters(0)
    assert (screen.cursor.y, screen.cursor.x) == (1, 1)
    assert screen.display == ["  m", "i  ", "fo "]

    # ! extreme cases.
    screen = update(pyte.Screen(5, 1), ["12345"], colored=[0])
    screen.cursor.x = 1
    screen.erase_characters(3)
    assert (screen.cursor.y, screen.cursor.x) == (0, 1)
    assert screen.display == ["1   5"]
    assert tolist(screen)[0] == [
        Char("1", fg="red"),
        screen.default_char,
        screen.default_char,
        screen.default_char,
        Char("5", "red")
    ]

    screen = update(pyte.Screen(5, 1), ["12345"], colored=[0])
    screen.cursor.x = 2
    screen.erase_characters(10)
    assert (screen.cursor.y, screen.cursor.x) == (0, 2)
    assert screen.display == ["12   "]
    assert tolist(screen)[0] == [
        Char("1", fg="red"),
        Char("2", fg="red"),
        screen.default_char,
        screen.default_char,
        screen.default_char
    ]

    screen = update(pyte.Screen(5, 1), ["12345"], colored=[0])
    screen.erase_characters(4)
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["    5"]
    assert tolist(screen)[0] == [
        screen.default_char,
        screen.default_char,
        screen.default_char,
        screen.default_char,
        Char("5", fg="red")
    ]


def test_erase_in_line():
    screen = update(pyte.Screen(5, 5),
                    ["sam i",
                     "s foo",
                     "but a",
                     "re yo",
                     "u?   "], colored=[0])
    screen.cursor_position(1, 3)

    # a) erase from cursor to the end of line
    screen.erase_in_line(0)
    assert (screen.cursor.y, screen.cursor.x) == (0, 2)
    assert screen.display == ["sa   ",
                              "s foo",
                              "but a",
                              "re yo",
                              "u?   "]
    assert tolist(screen)[0] == [
        Char("s", fg="red"),
        Char("a", fg="red"),
        screen.default_char,
        screen.default_char,
        screen.default_char
    ]

    # b) erase from the beginning of the line to the cursor
    screen = update(screen,
                    ["sam i",
                     "s foo",
                     "but a",
                     "re yo",
                     "u?   "], colored=[0])
    screen.erase_in_line(1)
    assert (screen.cursor.y, screen.cursor.x) == (0, 2)
    assert screen.display == ["    i",
                              "s foo",
                              "but a",
                              "re yo",
                              "u?   "]
    assert tolist(screen)[0] == [
        screen.default_char,
        screen.default_char,
        screen.default_char,
        Char(" ", fg="red"),
        Char("i", fg="red")
    ]

    # c) erase the entire line
    screen = update(screen,
                    ["sam i",
                     "s foo",
                     "but a",
                     "re yo",
                     "u?   "], colored=[0])
    screen.erase_in_line(2)
    assert (screen.cursor.y, screen.cursor.x) == (0, 2)
    assert screen.display == ["     ",
                              "s foo",
                              "but a",
                              "re yo",
                              "u?   "]
    assert tolist(screen)[0] == [screen.default_char] * 5


def test_erase_in_display():
    screen = update(pyte.Screen(5, 5),
                    ["sam i",
                     "s foo",
                     "but a",
                     "re yo",
                     "u?   "], colored=[2, 3])
    screen.cursor_position(3, 3)

    # a) erase from cursor to the end of the display, including
    #    the cursor
    screen.erase_in_display(0)
    assert (screen.cursor.y, screen.cursor.x) == (2, 2)
    assert screen.display == ["sam i",
                              "s foo",
                              "bu   ",
                              "     ",
                              "     "]
    assert tolist(screen)[2:] == [
        [Char("b", fg="red"),
         Char("u", fg="red"),
         screen.default_char,
         screen.default_char,
         screen.default_char],
        [screen.default_char] * 5,
        [screen.default_char] * 5
    ]

    # b) erase from the beginning of the display to the cursor,
    #    including it
    screen = update(screen,
                    ["sam i",
                     "s foo",
                     "but a",
                     "re yo",
                     "u?   "], colored=[2, 3])
    screen.erase_in_display(1)
    assert (screen.cursor.y, screen.cursor.x) == (2, 2)
    assert screen.display == ["     ",
                              "     ",
                              "    a",
                              "re yo",
                              "u?   "]
    assert tolist(screen)[:3] == [
        [screen.default_char] * 5,
        [screen.default_char] * 5,
        [screen.default_char,
         screen.default_char,
         screen.default_char,
         Char(" ", fg="red"),
         Char("a", fg="red")],
    ]

    # c) erase the while display
    screen.erase_in_display(2)
    assert (screen.cursor.y, screen.cursor.x) == (2, 2)
    assert screen.display == ["     ",
                              "     ",
                              "     ",
                              "     ",
                              "     "]
    assert tolist(screen) == [[screen.default_char] * 5] * 5

    # d) erase with private mode
    screen = update(pyte.Screen(5, 5),
                    ["sam i",
                     "s foo",
                     "but a",
                     "re yo",
                     "u?   "], colored=[2, 3])
    screen.erase_in_display(3, private=True)
    assert screen.display == ["     ",
                              "     ",
                              "     ",
                              "     ",
                              "     "]

    # e) erase with extra args
    screen = update(pyte.Screen(5, 5),
                    ["sam i",
                     "s foo",
                     "but a",
                     "re yo",
                     "u?   "], colored=[2, 3])
    args = [3, 0]
    screen.erase_in_display(*args)
    assert screen.display == ["     ",
                              "     ",
                              "     ",
                              "     ",
                              "     "]

    # f) erase with extra args and private
    screen = update(pyte.Screen(5, 5),
                    ["sam i",
                     "s foo",
                     "but a",
                     "re yo",
                     "u?   "], colored=[2, 3])
    screen.erase_in_display(*args, private=True)
    assert screen.display == ["     ",
                              "     ",
                              "     ",
                              "     ",
                              "     "]


def test_cursor_up():
    screen = pyte.Screen(10, 10)

    # Moving the cursor up at the top doesn't do anything
    screen.cursor_up(1)
    assert screen.cursor.y == 0

    screen.cursor.y = 1

    # Moving the cursor past the top moves it to the top
    screen.cursor_up(10)
    assert screen.cursor.y == 0

    screen.cursor.y = 5
    # Can move the cursor more than one up.
    screen.cursor_up(3)
    assert screen.cursor.y == 2


def test_cursor_down():
    screen = pyte.Screen(10, 10)

    # Moving the cursor down at the bottom doesn't do anything
    screen.cursor.y = 9
    screen.cursor_down(1)
    assert screen.cursor.y == 9

    screen.cursor.y = 8

    # Moving the cursor past the bottom moves it to the bottom
    screen.cursor_down(10)
    assert screen.cursor.y == 9

    screen.cursor.y = 5
    # Can move the cursor more than one down.
    screen.cursor_down(3)
    assert screen.cursor.y == 8


def test_cursor_back():
    screen = pyte.Screen(10, 10)

    # Moving the cursor left at the margin doesn't do anything
    screen.cursor.x = 0
    screen.cursor_back(1)
    assert screen.cursor.x == 0

    screen.cursor.x = 3

    # Moving the cursor past the left margin moves it to the left margin
    screen.cursor_back(10)
    assert screen.cursor.x == 0

    screen.cursor.x = 5
    # Can move the cursor more than one back.
    screen.cursor_back(3)
    assert screen.cursor.x == 2


def test_cursor_back_last_column():
    screen = pyte.Screen(13, 1)
    screen.draw("Hello, world!")
    assert screen.cursor.x == screen.columns

    screen.cursor_back(5)
    assert screen.cursor.x == (screen.columns - 1) - 5


def test_cursor_forward():
    screen = pyte.Screen(10, 10)

    # Moving the cursor right at the margin doesn't do anything
    screen.cursor.x = 9
    screen.cursor_forward(1)
    assert screen.cursor.x == 9

    # Moving the cursor past the right margin moves it to the right margin
    screen.cursor.x = 8
    screen.cursor_forward(10)
    assert screen.cursor.x == 9

    # Can move the cursor more than one forward.
    screen.cursor.x = 5
    screen.cursor_forward(3)
    assert screen.cursor.x == 8


def test_cursor_position():
    screen = pyte.Screen(10, 10)

    # a) testing that we expect 1-indexed values
    screen.cursor_position(5, 10)
    assert (screen.cursor.y, screen.cursor.x) == (4, 9)

    # b) but (0, 0) is also accepted and should be the same as (1, 1)
    screen.cursor_position(0, 10)
    assert (screen.cursor.y, screen.cursor.x) == (0, 9)

    # c) moving outside the margins constrains to within the screen
    #    bounds
    screen.cursor_position(100, 5)
    assert (screen.cursor.y, screen.cursor.x) == (9, 4)

    screen.cursor_position(5, 100)
    assert (screen.cursor.y, screen.cursor.x) == (4, 9)

    # d) DECOM on
    screen.set_margins(5, 9)
    screen.set_mode(mo.DECOM)
    screen.cursor_position()
    assert (screen.cursor.y, screen.cursor.x) == (4, 0)

    screen.cursor_position(2, 0)
    assert (screen.cursor.y, screen.cursor.x) == (5, 0)

    # Note that cursor position doesn't change.
    screen.cursor_position(10, 0)
    assert (screen.cursor.y, screen.cursor.x) == (5, 0)


def test_unicode():
    screen = pyte.Screen(4, 2)
    stream = pyte.ByteStream(screen)

    stream.feed("тест".encode())
    assert screen.display == ["тест", "    "]


def test_alignment_display():
    screen = pyte.Screen(5, 5)
    screen.set_mode(mo.LNM)
    screen.draw("a")
    screen.linefeed()
    screen.linefeed()
    screen.draw("b")

    assert screen.display == ["a    ",
                              "     ",
                              "b    ",
                              "     ",
                              "     "]

    screen.alignment_display()

    assert screen.display == ["EEEEE",
                              "EEEEE",
                              "EEEEE",
                              "EEEEE",
                              "EEEEE"]


def test_set_margins():
    screen = pyte.Screen(10, 10)

    assert screen.margins is None

    # a) ok-case
    screen.set_margins(1, 5)
    assert screen.margins == (0, 4)

    # b) one of the margins is out of bounds
    screen.set_margins(100, 10)
    assert screen.margins != (99, 9)
    assert screen.margins == (0, 4)

    # c) no margins provided -- reset to full screen.
    screen.set_margins()
    assert screen.margins is None


def test_set_margins_zero():
    # See https://github.com/selectel/pyte/issues/61
    screen = pyte.Screen(80, 24)
    screen.set_margins(1, 5)
    assert screen.margins == (0, 4)
    screen.set_margins(0)
    assert screen.margins is None


def test_hide_cursor():
    screen = pyte.Screen(10, 10)

    # DECTCEM is set by default.
    assert mo.DECTCEM in screen.mode
    assert not screen.cursor.hidden

    # a) resetting DECTCEM hides the cursor.
    screen.reset_mode(mo.DECTCEM)
    assert screen.cursor.hidden

    # b) ... and it's back!
    screen.set_mode(mo.DECTCEM)
    assert not screen.cursor.hidden


def test_report_device_attributes():
    screen = pyte.Screen(10, 10)

    acc = []
    screen.write_process_input = acc.append

    # a) noop
    screen.report_device_attributes(42)
    assert not acc

    # b) OK case
    screen.report_device_attributes()
    assert acc.pop() == ctrl.CSI + "?6c"


def test_report_device_status():
    screen = pyte.Screen(10, 10)

    acc = []
    screen.write_process_input = acc.append

    # a) noop
    screen.report_device_status(42)
    assert not acc

    # b) terminal status
    screen.report_device_status(5)
    assert acc.pop() == ctrl.CSI + "0n"

    # c) cursor position, DECOM off
    screen.cursor_to_column(5)
    screen.report_device_status(6)
    assert acc.pop() == ctrl.CSI + f"{1};{5}R"

    # d) cursor position, DECOM on
    screen.cursor_position()
    screen.set_margins(5, 9)
    screen.set_mode(mo.DECOM)
    screen.cursor_to_line(5)
    screen.report_device_status(6)
    assert acc.pop() == ctrl.CSI + f"{5};{1}R"


def test_screen_set_icon_name_title():
    screen = pyte.Screen(10, 1)

    text = "±"
    screen.set_icon_name(text)
    assert screen.icon_name == text

    screen.set_title(text)
    assert screen.title == text


def test_private_sgr_sequence_ignored():
    def cursor_state(cursor):
        return (cursor.x, cursor.y, cursor.attrs, cursor.hidden)

    screen = pyte.HistoryScreen(2, 2)
    stream = pyte.ByteStream(screen)

    # Capture initial state
    display = screen.display
    mode = screen.mode.copy()
    cursor = cursor_state(screen.cursor)

    # Vim 9.0+ sends this to query modifyOtherKeys capability - should be ignored
    stream.feed(b'\x1b[?4m')

    # Verify nothing changed
    assert screen.display == display
    assert screen.mode == mode
    assert cursor_state(screen.cursor) == cursor


def test_alternate_screen_buffer():
    # Entering saves the primary screen and starts from an empty alternate one.
    screen = update(pyte.Screen(4, 2), ["main", "text"])
    assert not screen.alternate_screen

    screen.set_mode(mo.ALTBUF_1049)
    assert screen.alternate_screen
    assert screen.display == ["    ", "    "]

    # ... and the primary screen comes back untouched on the way out.
    screen.draw("alt")
    assert screen.display == ["alt ", "    "]
    screen.reset_mode(mo.ALTBUF_1049)
    assert not screen.alternate_screen
    assert screen.display == ["main", "text"]


def test_alternate_screen_buffer_does_not_home_cursor():
    # xterm clears the alternate buffer without homing the cursor, and both
    # tmux 3.6b and GNU screen agree: text drawn right after entering lands on
    # the row the cursor was already on.
    screen = pyte.Screen(4, 3)
    screen.draw("ab")
    screen.carriage_return()
    screen.linefeed()
    assert (screen.cursor.y, screen.cursor.x) == (1, 0)

    screen.set_mode(mo.ALTBUF_1049)
    assert screen.cursor.y == 1
    screen.draw("alt")
    assert screen.display == ["    ", "alt ", "    "]


def test_alternate_screen_buffer_cursor_save_restore():
    # 1049 is defined as 1047 combined with 1048, so it saves and restores the
    # cursor; 47 does neither.
    screen = pyte.Screen(6, 3)
    screen.cursor_position(3, 5)
    screen.set_mode(mo.ALTBUF_1049)
    screen.cursor_position(1, 1)
    screen.reset_mode(mo.ALTBUF_1049)
    assert (screen.cursor.y, screen.cursor.x) == (2, 4)

    screen = pyte.Screen(6, 3)
    screen.cursor_position(3, 5)
    screen.set_mode(mo.ALTBUF_47)
    screen.cursor_position(1, 1)
    screen.reset_mode(mo.ALTBUF_47)
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)


def test_alternate_screen_buffer_1048_only_moves_cursor():
    # 1048 saves/restores the cursor without switching buffers at all.
    screen = update(pyte.Screen(4, 2), ["main", "text"])
    screen.cursor_position(2, 3)
    screen.set_mode(mo.ALTBUF_1048)
    assert not screen.alternate_screen
    assert screen.display == ["main", "text"]

    screen.cursor_position(1, 1)
    screen.reset_mode(mo.ALTBUF_1048)
    assert (screen.cursor.y, screen.cursor.x) == (1, 2)
    assert screen.display == ["main", "text"]


def test_alternate_screen_buffer_is_idempotent():
    # A program emitting 1049h twice must not lose the primary screen -- if the
    # second entry overwrote the saved buffer, exiting would restore the
    # alternate screen instead.
    screen = update(pyte.Screen(4, 2), ["main", "text"])
    screen.set_mode(mo.ALTBUF_1049)
    screen.draw("alt")
    screen.set_mode(mo.ALTBUF_1049)
    screen.reset_mode(mo.ALTBUF_1049)
    assert screen.display == ["main", "text"]

    # Leaving twice is equally harmless.
    screen.reset_mode(mo.ALTBUF_1049)
    assert not screen.alternate_screen
    assert screen.display == ["main", "text"]


def test_alternate_screen_buffer_leaving_without_entering():
    screen = update(pyte.Screen(4, 2), ["main", "text"])
    screen.reset_mode(mo.ALTBUF_1049)
    assert not screen.alternate_screen
    assert screen.display == ["main", "text"]


@pytest.mark.parametrize("enter", [mo.ALTBUF_47, mo.ALTBUF_1047, mo.ALTBUF_1049])
@pytest.mark.parametrize("leave", [mo.ALTBUF_47, mo.ALTBUF_1047, mo.ALTBUF_1049])
def test_alternate_screen_buffer_modes_share_one_switch(enter, leave):
    # The reference emulators keep a single buffer-switch flag rather than
    # per-mode state, so any of the three modes leaves a buffer entered with any
    # other (measured on tmux 3.6b and GNU screen 4.00.03).
    screen = update(pyte.Screen(4, 2), ["main", "text"])
    screen.set_mode(enter)
    assert screen.alternate_screen
    screen.draw("alt")
    screen.reset_mode(leave)
    assert not screen.alternate_screen
    assert screen.display == ["main", "text"]


def test_alternate_screen_buffer_not_kept_across_a_round_trip():
    # Re-entering shows an EMPTY alternate screen, whichever mode is used. The
    # xterm docs' "without clearing" wording for 47/1047 describes clearing, not
    # buffer lifetime; both reference emulators discard the contents.
    screen = pyte.Screen(8, 2)
    screen.set_mode(mo.ALTBUF_47)
    screen.draw("altdata")
    screen.reset_mode(mo.ALTBUF_47)
    screen.set_mode(mo.ALTBUF_47)
    assert screen.display == ["        ", "        "]


def test_alternate_screen_buffer_reset_leaves_it():
    # RIS returns to the primary screen; both buffers are discarded.
    screen = update(pyte.Screen(4, 2), ["main", "text"])
    screen.set_mode(mo.ALTBUF_1049)
    screen.draw("alt")
    screen.reset()
    assert not screen.alternate_screen
    assert screen.display == ["    ", "    "]


def test_alternate_screen_buffer_resize_clips_offscreen_buffer():
    # Resizing while on the alternate screen must clip the saved primary one
    # too, or exiting would restore a screen of the wrong shape. The expected
    # value is taken from resizing WITHOUT entering the alternate screen rather
    # than written by hand, so it cannot encode a bug in the clipping code.
    def build():
        return update(pyte.Screen(6, 3), ["primar", "second", "third "])

    direct = build()
    direct.resize(columns=3, lines=2)
    expected = list(direct.display)

    screen = build()
    screen.set_mode(mo.ALTBUF_1049)
    screen.resize(columns=3, lines=2)
    screen.reset_mode(mo.ALTBUF_1049)
    assert screen.columns == 3
    assert screen.display == expected
    for line in screen.buffer.values():
        assert all(x < 3 for x in line)


def test_alternate_screen_buffer_via_escape_sequences():
    # End to end through the stream, which is how a real program drives this:
    # `vim`, `less` and `htop` all emit exactly these two sequences.
    screen = pyte.Screen(5, 2)
    stream = pyte.ByteStream(screen)
    stream.feed(b"main\r\n")
    assert screen.display == ["main ", "     "]

    stream.feed(b"\x1b[?1049h")
    assert screen.alternate_screen
    assert screen.display == ["     ", "     "]

    stream.feed(b"ALT")
    assert screen.display == ["     ", "ALT  "]

    stream.feed(b"\x1b[?1049l")
    assert not screen.alternate_screen
    assert screen.display == ["main ", "     "]


def test_alternate_screen_buffer_cursor_survives_inner_decsc():
    # Full-screen programs use DECSC *inside* the alternate screen constantly.
    # If 1049 shared the `savepoints` stack with DECSC, an unbalanced ESC 7 in
    # there would leave the wrong savepoint on top and exiting would restore the
    # program's internal cursor instead of the shell's. Measured on tmux 3.6b:
    # the cursor comes back to where it was before entering.
    screen = pyte.Screen(20, 5)
    stream = pyte.ByteStream(screen)
    stream.feed(b"\x1b[3;7H")
    assert (screen.cursor.y, screen.cursor.x) == (2, 6)

    stream.feed(b"\x1b[?1049h")
    stream.feed(b"\x1b[1;1H\x1b7")          # DECSC inside the alternate screen
    stream.feed(b"\x1b[?1049l")
    assert (screen.cursor.y, screen.cursor.x) == (2, 6)

    stream.feed(b"X")
    assert screen.display[2].startswith("      X")


def test_alternate_screen_buffer_unpaired_exit_keeps_cursor():
    # A stray 1049l with no matching 1049h must not move the cursor. Falling
    # through to restore_cursor's empty-stack behaviour would home it.
    screen = pyte.Screen(10, 4)
    screen.cursor_position(3, 5)
    screen.reset_mode(mo.ALTBUF_1049)
    assert (screen.cursor.y, screen.cursor.x) == (2, 4)


def test_alternate_screen_buffer_resize_shrink_drops_from_top():
    # Shrinking drops rows from the TOP; the saved primary buffer must be
    # clipped the same way the displayed one is, or exiting restores the wrong
    # half. Compared against resizing without ever entering the alternate screen.
    def build():
        s = pyte.Screen(6, 4)
        pyte.ByteStream(s).feed(b"AAA\r\nBBB\r\nCCC\r\nDDD")
        return s

    direct = build()
    direct.resize(lines=2, columns=6)
    expected = [row.rstrip() for row in direct.display]

    via_alt = build()
    via_alt.set_mode(mo.ALTBUF_1049)
    via_alt.resize(lines=2, columns=6)
    via_alt.reset_mode(mo.ALTBUF_1049)
    assert [row.rstrip() for row in via_alt.display] == expected == ["CCC", "DDD"]


def test_alternate_screen_buffer_nested_entry_keeps_first_cursor():
    # A program emitting smcup twice must not lose the shell's cursor. Measured
    # on tmux 3.6b: `ESC[3;7H smcup ESC[5;15H smcup rmcup` restores the cursor to
    # row 3 col 7 -- identical to the single-smcup case, so the second entry does
    # not re-save. The buffer switch was already idempotent; the cursor save was
    # not, which made the two disagree.
    screen = pyte.Screen(20, 6)
    stream = pyte.ByteStream(screen)
    stream.feed(b"\x1b[3;7H\x1b[?1049h\x1b[5;15H\x1b[?1049h\x1b[?1049lX")
    assert (screen.cursor.y, screen.cursor.x) == (2, 7)
    assert screen.display[2].startswith("      X")

    # 1048 on its own is an explicit DECSC and must still re-save -- including
    # while the alternate screen is already up, which is where a full-screen
    # program would use it. Suppressing 1048 along with the nested 1049 would be
    # an over-correction, so both cases are pinned.
    screen = pyte.Screen(20, 6)
    stream = pyte.ByteStream(screen)
    stream.feed(b"\x1b[2;5H\x1b[?1048h\x1b[5;1Hjunk\x1b[?1048lX")
    assert screen.display[1].startswith("    X")

    screen = pyte.Screen(20, 6)
    stream = pyte.ByteStream(screen)
    stream.feed(b"\x1b[?1049h")            # already on the alternate screen
    stream.feed(b"\x1b[2;5H\x1b[?1048h")  # explicit DECSC in here must save
    stream.feed(b"\x1b[5;1Hjunk\x1b[?1048lX")
    assert screen.display[1].startswith("    X"), screen.display[:3]


@pytest.mark.parametrize("enter,leave", [(b"\x1b[?5h", b"\x1b[?5l"),
                                         (b"\x1b[?5l", b"\x1b[?5h")])
def test_alternate_screen_buffer_decscnm_reaches_both_buffers(enter, leave):
    # DECSCNM is a property of the SCREEN, but pyte realises it by rewriting each
    # cell. Rewriting only the displayed buffer left the other one disagreeing
    # with self.mode, so a program that toggled reverse video while on the
    # alternate screen restored a primary screen whose cells contradicted the
    # mode bit. Compared against never entering the alternate screen at all.
    def build(via_alt):
        s = pyte.Screen(4, 2)
        st = pyte.ByteStream(s)
        st.feed(enter + b"ab")
        if via_alt:
            st.feed(b"\x1b[?1049h" + leave + b"\x1b[?1049l")
        else:
            st.feed(leave)
        return s

    direct, via_alt = build(False), build(True)
    assert [via_alt.buffer[0][x].reverse for x in range(4)] == \
           [direct.buffer[0][x].reverse for x in range(4)]
    assert via_alt.buffer[0].default.reverse == direct.buffer[0].default.reverse


def test_alternate_screen_buffer_1048_does_not_clobber_1049():
    # 1048 is an independent DECSC that a program may issue WHILE the alternate
    # screen is up, so it must not overwrite the cursor 1049 saved for the shell.
    # Sharing one slot reintroduced exactly the defect the dedicated slot was
    # added to fix for `ESC 7`, one commit earlier.
    def cursor_after(payload):
        screen = pyte.Screen(20, 8)
        pyte.ByteStream(screen).feed(payload)
        return (screen.cursor.y, screen.cursor.x)

    base = b"\x1b[3;7H\x1b[?1049h\x1b[5;15H"
    control = cursor_after(base + b"\x1b[?1049l")
    assert control == (2, 6)
    # DECSC inside the alternate screen: already covered, kept as the reference.
    assert cursor_after(base + b"\x1b7\x1b[?1049l") == control
    # 1048 inside the alternate screen must behave the same way.
    assert cursor_after(base + b"\x1b[?1048h\x1b[?1049l") == control
    assert cursor_after(base + b"\x1b[?1048h\x1b[?1048l\x1b[?1049l") == control

    # 1048 must still SAVE while the alternate screen is up — suppressing it
    # there would be an over-correction, and the paired case above cannot tell
    # the difference (a suppressed save leaves an empty slot, so the restore is
    # inert and 1049 supplies the same answer either way). This asserts the save
    # actually happened, by moving between 1048h and 1048l.
    screen = pyte.Screen(20, 8)
    stream = pyte.ByteStream(screen)
    stream.feed(b"\x1b[?1049h\x1b[2;5H\x1b[?1048h")
    stream.feed(b"\x1b[6;1Hjunk\x1b[?1048lX")
    assert screen.display[1].startswith("    X"), screen.display[:3]

    # And 1048 must still work on its own, with an unpaired reset staying inert.
    screen = pyte.Screen(20, 6)
    pyte.ByteStream(screen).feed(
        b"\x1b[2;5H\x1b[?1048h\x1b[5;1Hjunk\x1b[?1048lX")
    assert screen.display[1].startswith("    X")

    screen = pyte.Screen(20, 8)
    pyte.ByteStream(screen).feed(b"\x1b[4;9H\x1b[?1048l")
    assert (screen.cursor.y, screen.cursor.x) == (3, 8)
