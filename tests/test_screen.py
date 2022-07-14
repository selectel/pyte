import copy, sys, os, itertools

import pytest

import pyte
from pyte import modes as mo, control as ctrl, graphics as g
from pyte.screens import Char as _orig_Char, CharStyle

sys.path.append(os.path.join(os.path.dirname(__file__), "helpers"))
from asserts import consistency_asserts, splice

# Implement the old API of Char so we don't have to change
# all the tests
class Char(_orig_Char):
    def __init__(self, data=" ", fg="default", bg="default", bold=False, italics=False, underscore=False,
                strikethrough=False, reverse=False, blink=False, width=1):
        self.data = data
        self.width = width
        self.style = CharStyle(fg, bg, bold, italics, underscore, strikethrough, reverse, blink)


# Test helpers.

def update(screen, lines, colored=[], write_spaces=True):
    """Updates a given screen object with given lines, colors each line
    from ``colored`` in "red" and returns the modified screen.
    """
    base_style = Char().style
    red_style = base_style._replace(fg="red")
    for y, line in enumerate(lines):
        for x, char in enumerate(line):
            if y in colored:
                style = red_style
            else:
                style = base_style
            # Note: this hack is only for testing purposes.
            # Modifying the screen's buffer is not allowed.
            if char == ' ' and not write_spaces:
                # skip, leave the default char in the screen
                pass
            else:
                screen._buffer.line_at(y).write_data(x, char, 1, style)

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
    assert screen.margins == (0, 1)
    screen.set_mode(mo.DECOM)
    screen.set_margins(0, 1)
    assert screen.margins == (0, 1)
    assert screen.columns == screen.lines == 2
    assert tolist(screen) == [[screen.default_char, screen.default_char]] * 2
    consistency_asserts(screen)

    screen.resize(3, 3)
    assert screen.columns == screen.lines == 3
    assert tolist(screen) == [
        [screen.default_char, screen.default_char, screen.default_char]
    ] * 3
    assert mo.DECOM in screen.mode
    assert screen.margins == (0, 2)
    consistency_asserts(screen)

    screen.resize(2, 2)
    assert screen.columns == screen.lines == 2
    assert tolist(screen) == [[screen.default_char, screen.default_char]] * 2
    consistency_asserts(screen)

    # Quirks:
    # a) if the current display is narrower than the requested size,
    #    new columns should be added to the right.
    screen = update(pyte.Screen(2, 2), ["bo", "sh"], [None, None])
    screen.resize(2, 3)
    assert screen.display == ["bo ", "sh "]
    consistency_asserts(screen)

    # b) if the current display is wider than the requested size,
    #    columns should be removed from the right...
    screen = update(pyte.Screen(2, 2), ["bo", "sh"], [None, None])
    screen.resize(2, 1)
    assert screen.display == ["b", "s"]
    consistency_asserts(screen)

    # c) if the current display is shorter than the requested
    #    size, new rows should be added on the bottom.
    screen = update(pyte.Screen(2, 2), ["bo", "sh"], [None, None])
    screen.resize(3, 2)

    assert screen.display == ["bo", "sh", "  "]
    consistency_asserts(screen)

    # d) if the current display is taller than the requested
    #    size, rows should be removed from the top.
    screen = update(pyte.Screen(2, 2), ["bo", "sh"], [None, None])
    screen.resize(1, 2)
    assert screen.display == ["sh"]
    consistency_asserts(screen)


def test_resize_same():
    screen = pyte.Screen(2, 2)
    screen.dirty.clear()
    screen.resize(2, 2)
    assert not screen.dirty
    consistency_asserts(screen)


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
    consistency_asserts(screen)

    # ... one` more character -- now we got a linefeed!
    screen.draw("a")
    assert (screen.cursor.y, screen.cursor.x) == (1, 1)
    consistency_asserts(screen)

    # ``DECAWM`` is off.
    screen = pyte.Screen(3, 3)
    screen.reset_mode(mo.DECAWM)

    for ch in "abc":
        screen.draw(ch)

    assert screen.display == ["abc", "   ", "   "]
    assert (screen.cursor.y, screen.cursor.x) == (0, 3)
    consistency_asserts(screen)

    # No linefeed is issued on the end of the line ...
    screen.draw("a")
    assert screen.display == ["aba", "   ", "   "]
    assert (screen.cursor.y, screen.cursor.x) == (0, 3)
    consistency_asserts(screen)

    # ``IRM`` mode is on, expecting new characters to move the old ones
    # instead of replacing them.
    screen.set_mode(mo.IRM)
    screen.cursor_position()
    screen.draw("x")
    assert screen.display == ["xab", "   ", "   "]
    consistency_asserts(screen)

    screen.cursor_position()
    screen.draw("y")
    assert screen.display == ["yxa", "   ", "   "]
    consistency_asserts(screen)


def test_draw_russian():
    # Test from https://github.com/selectel/pyte/issues/65
    screen = pyte.Screen(20, 1)
    stream = pyte.Stream(screen)
    stream.feed("Нерусский текст")
    assert screen.display == ["Нерусский текст     "]
    consistency_asserts(screen)


def test_draw_multiple_chars():
    screen = pyte.Screen(10, 1)
    screen.draw("foobar")
    assert screen.cursor.x == 6
    assert screen.display == ["foobar    "]
    consistency_asserts(screen)


def test_draw_utf8():
    # See https://github.com/selectel/pyte/issues/62
    screen = pyte.Screen(1, 1)
    stream = pyte.ByteStream(screen)
    stream.feed(b"\xE2\x80\x9D")
    assert screen.display == ["”"]
    consistency_asserts(screen)


def test_draw_width2():
    # Example from https://github.com/selectel/pyte/issues/9
    screen = pyte.Screen(10, 1)
    screen.draw("コンニチハ")
    assert screen.cursor.x == screen.columns
    consistency_asserts(screen)


def test_draw_width2_line_end():
    # Test from https://github.com/selectel/pyte/issues/55
    screen = pyte.Screen(10, 1)
    screen.draw(" コンニチハ")
    assert screen.cursor.x == screen.columns
    consistency_asserts(screen)


@pytest.mark.xfail
def test_draw_width2_irm():
    screen = pyte.Screen(2, 1)
    screen.draw("コ")
    assert screen.display == ["コ"]
    assert tolist(screen) == [[Char("コ"), Char(" ")]]
    consistency_asserts(screen)

    # Overwrite the stub part of a width 2 character.
    screen.set_mode(mo.IRM)
    screen.cursor_to_column(screen.columns)
    screen.draw("x")
    assert screen.display == [" x"]
    consistency_asserts(screen)


def test_draw_width0_combining():
    screen = pyte.Screen(4, 2)

    # a) no prev. character
    screen.draw("\N{COMBINING DIAERESIS}")
    assert screen.display == ["    ", "    "]
    consistency_asserts(screen)

    screen.draw("bad")

    # b) prev. character is on the same line
    screen.draw("\N{COMBINING DIAERESIS}")
    assert screen.display == ["bad̈ ", "    "]
    consistency_asserts(screen)

    # c) prev. character is on the prev. line
    screen.draw("!")
    screen.draw("\N{COMBINING DIAERESIS}")
    assert screen.display == ["bad̈!̈", "    "]
    consistency_asserts(screen)


def test_draw_width0_irm():
    screen = pyte.Screen(10, 1)
    screen.set_mode(mo.IRM)

    # The following should not insert any blanks.
    screen.draw("\N{ZERO WIDTH SPACE}")
    screen.draw("\u0007")  # DELETE.
    assert screen.display == [" " * screen.columns]
    consistency_asserts(screen)


def test_draw_width0_decawm_off():
    screen = pyte.Screen(10, 1)
    screen.reset_mode(mo.DECAWM)
    screen.draw(" コンニチハ")
    assert screen.cursor.x == screen.columns
    consistency_asserts(screen)

    # The following should not advance the cursor.
    screen.draw("\N{ZERO WIDTH SPACE}")
    screen.draw("\u0007")  # DELETE.
    assert screen.cursor.x == screen.columns
    consistency_asserts(screen)


def test_draw_cp437():
    screen = pyte.Screen(5, 1)
    stream = pyte.ByteStream(screen)
    assert screen.charset == 0

    screen.define_charset("U", "(")
    stream.select_other_charset("@")
    stream.feed("α ± ε".encode("cp437"))

    assert screen.display == ["α ± ε"]
    consistency_asserts(screen)


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
    consistency_asserts(screen)


def test_display_wcwidth():
    screen = pyte.Screen(10, 1)
    screen.draw("コンニチハ")
    assert screen.display == ["コンニチハ"]
    consistency_asserts(screen)


def test_carriage_return():
    screen = pyte.Screen(3, 3)
    screen.cursor.x = 2
    screen.carriage_return()

    assert screen.cursor.x == 0
    consistency_asserts(screen)


def test_index():
    screen = update(pyte.Screen(2, 2), ["wo", "ot"], colored=[1])
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["wo", "ot"]

    # a) indexing on a row that isn't the last should just move
    # the cursor down.
    screen.index()
    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["wo", "ot"]
    assert tolist(screen) == [
        [Char("w"), Char("o")],
        [Char("o", fg="red"), Char("t", fg="red")]
    ]
    consistency_asserts(screen)

    # b) indexing on the last row should push everything up and
    # create a new row at the bottom.
    screen.index()
    assert screen.cursor.y == 1
    assert screen.display == ["ot", "  "]
    assert tolist(screen) == [
        [Char("o", fg="red"), Char("t", fg="red")],
        [screen.default_char, screen.default_char]
    ]
    consistency_asserts(screen)

    # c) same with margins
    screen = update(pyte.Screen(2, 5), ["bo", "sh", "th", "er", "oh"],
                    colored=[1, 2])
    # note: margins are 0-based inclusive indexes for top and bottom
    # however, set_margins are 1-based inclusive indexes
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
    consistency_asserts(screen)

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
    consistency_asserts(screen)

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
    consistency_asserts(screen)

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
    consistency_asserts(screen)


def test_index_sparse():
    screen = update(pyte.Screen(5, 5),
            ["wo   ",
             "     ",
             " o t ",
             "     ",
             "x   z",
             ],
            colored=[2],
            write_spaces=False)
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == [
            "wo   ",
            "     ",
            " o t ",
            "     ",
            "x   z",
            ]

    # a) indexing on a row that isn't the last should just move
    # the cursor down.
    screen.index()
    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == [
            "wo   ",
            "     ",
            " o t ",
            "     ",
            "x   z",
            ]
    assert tolist(screen) == [
        [Char("w"), Char("o"),] + [screen.default_char] * 3,
        [screen.default_char] * 5,
        [screen.default_char, Char("o", fg="red"), screen.default_char, Char("t", fg="red"), screen.default_char],
        [screen.default_char] * 5,
        [Char("x")] + [screen.default_char] * 3 + [Char("z")],
    ]
    consistency_asserts(screen)

    # b) indexing on the last row should push everything up and
    # create a new row at the bottom.
    screen.index()
    screen.index()
    screen.index()
    screen.index()
    assert screen.cursor.y == 4
    assert screen.display == [
            "     ",
            " o t ",
            "     ",
            "x   z",
            "     ",
            ]
    assert tolist(screen) == [
        [screen.default_char] * 5,
        [screen.default_char, Char("o", fg="red"), screen.default_char, Char("t", fg="red"), screen.default_char],
        [screen.default_char] * 5,
        [Char("x")] + [screen.default_char] * 3 + [Char("z")],
        [screen.default_char] * 5,
    ]
    consistency_asserts(screen)

    # again
    screen.index()
    assert screen.cursor.y == 4
    assert screen.display == [
            " o t ",
            "     ",
            "x   z",
            "     ",
            "     ",
            ]
    assert tolist(screen) == [
        [screen.default_char, Char("o", fg="red"), screen.default_char, Char("t", fg="red"), screen.default_char],
        [screen.default_char] * 5,
        [Char("x")] + [screen.default_char] * 3 + [Char("z")],
        [screen.default_char] * 5,
        [screen.default_char] * 5,
    ]
    consistency_asserts(screen)

    # leave the screen cleared
    screen.index()
    screen.index()
    screen.index()
    assert (screen.cursor.y, screen.cursor.x) == (4, 0)
    assert screen.display == [
            "     ",
            "     ",
            "     ",
            "     ",
            "     ",
            ]
    assert tolist(screen) == [
        [screen.default_char] * 5,
        [screen.default_char] * 5,
        [screen.default_char] * 5,
        [screen.default_char] * 5,
        [screen.default_char] * 5,
    ]
    consistency_asserts(screen)


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
    consistency_asserts(screen)

    # b) once again ...
    screen.reverse_index()
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert tolist(screen) == [
        [screen.default_char, screen.default_char],
        [screen.default_char, screen.default_char],
    ]
    consistency_asserts(screen)

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
    consistency_asserts(screen)

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
    consistency_asserts(screen)

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
    consistency_asserts(screen)

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
    consistency_asserts(screen)


def test_reverse_index_sparse():
    screen = update(pyte.Screen(5, 5),
            ["wo   ",
             "     ",
             " o t ",
             "     ",
             "x   z",
             ],
            colored=[2],
            write_spaces=False)
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == [
            "wo   ",
            "     ",
            " o t ",
            "     ",
            "x   z",
            ]
    consistency_asserts(screen)

    # a) reverse indexing on the first row should push rows down
    # and create a new row at the top.
    screen.reverse_index()
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == [
            "     ",
            "wo   ",
            "     ",
            " o t ",
            "     ",
            ]
    assert tolist(screen) == [
        [screen.default_char] * 5,
        [Char("w"), Char("o"),] + [screen.default_char] * 3,
        [screen.default_char] * 5,
        [screen.default_char, Char("o", fg="red"), screen.default_char, Char("t", fg="red"), screen.default_char],
        [screen.default_char] * 5,
    ]
    consistency_asserts(screen)

    # again
    screen.reverse_index()
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == [
            "     ",
            "     ",
            "wo   ",
            "     ",
            " o t ",
            ]
    assert tolist(screen) == [
        [screen.default_char] * 5,
        [screen.default_char] * 5,
        [Char("w"), Char("o"),] + [screen.default_char] * 3,
        [screen.default_char] * 5,
        [screen.default_char, Char("o", fg="red"), screen.default_char, Char("t", fg="red"), screen.default_char],
    ]
    consistency_asserts(screen)

    # again
    screen.reverse_index()
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == [
            "     ",
            "     ",
            "     ",
            "wo   ",
            "     ",
            ]
    assert tolist(screen) == [
        [screen.default_char] * 5,
        [screen.default_char] * 5,
        [screen.default_char] * 5,
        [Char("w"), Char("o"),] + [screen.default_char] * 3,
        [screen.default_char] * 5,
    ]
    consistency_asserts(screen)

    # leave the screen cleared
    screen.reverse_index()
    screen.reverse_index()
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == [
            "     ",
            "     ",
            "     ",
            "     ",
            "     ",
            ]
    assert tolist(screen) == [
        [screen.default_char] * 5,
        [screen.default_char] * 5,
        [screen.default_char] * 5,
        [screen.default_char] * 5,
        [screen.default_char] * 5,
    ]
    consistency_asserts(screen)

def test_linefeed():
    screen = update(pyte.Screen(2, 2), ["bo", "sh"], [None, None])
    screen.set_mode(mo.LNM)

    # a) LNM on by default (that's what `vttest` forces us to do).
    assert mo.LNM in screen.mode
    screen.cursor.x, screen.cursor.y = 1, 0
    screen.linefeed()
    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    consistency_asserts(screen)

    # b) LNM off.
    screen.reset_mode(mo.LNM)
    screen.cursor.x, screen.cursor.y = 1, 0
    screen.linefeed()
    assert (screen.cursor.y, screen.cursor.x) == (1, 1)
    consistency_asserts(screen)


def test_linefeed_margins():
    # See issue #63 on GitHub.
    screen = pyte.Screen(80, 24)
    screen.set_margins(3, 27)
    screen.cursor_position()
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    consistency_asserts(screen)
    screen.linefeed()
    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    consistency_asserts(screen)


def test_tabstops():
    screen = pyte.Screen(10, 10)

    # Making sure initial tabstops are in place ...
    assert screen.tabstops == set([8])

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
    consistency_asserts(screen)


def test_clear_tabstops():
    screen = pyte.Screen(10, 10)
    screen.clear_tab_stop(3)

    # a) clear a tabstop at current cursor location
    screen.cursor.x = 1
    screen.set_tab_stop()
    screen.cursor.x = 5
    screen.set_tab_stop()
    screen.clear_tab_stop()

    assert screen.tabstops == set([1])
    consistency_asserts(screen)

    screen.set_tab_stop()
    screen.clear_tab_stop(0)

    assert screen.tabstops == set([1])

    # b) all tabstops
    screen.set_tab_stop()
    screen.cursor.x = 9
    screen.set_tab_stop()
    screen.clear_tab_stop(3)

    assert not screen.tabstops
    consistency_asserts(screen)


def test_backspace():
    screen = pyte.Screen(2, 2)
    assert screen.cursor.x == 0
    screen.backspace()
    assert screen.cursor.x == 0
    screen.cursor.x = 1
    screen.backspace()
    assert screen.cursor.x == 0
    consistency_asserts(screen)


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
    consistency_asserts(screen)


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
    consistency_asserts(screen)

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
    consistency_asserts(screen)


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
    consistency_asserts(screen)


    screen.insert_lines(1)
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["   ", "   ", "sam"]
    assert tolist(screen) == [
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [Char("s"), Char("a"), Char("m")]
    ]
    consistency_asserts(screen)

    screen.insert_lines(1)
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["   ", "   ", "   "]
    assert tolist(screen) == [
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [screen.default_char] * 3,
    ]
    consistency_asserts(screen)

    screen.insert_lines(1)
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["   ", "   ", "   "]
    assert tolist(screen) == [
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [screen.default_char] * 3,
    ]
    consistency_asserts(screen)

    screen = update(pyte.Screen(3, 3), ["sam", "is ", "foo"], colored=[1])
    screen.insert_lines(2)

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["   ", "   ", "sam"]
    assert tolist(screen) == [
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [Char("s"), Char("a"), Char("m")]
    ]
    consistency_asserts(screen)

    screen = update(pyte.Screen(3, 5), [
        "sam",
        "",     # an empty string will be interpreted as a full empty line
        "foo",
        "bar",
        "baz"
        ],
        colored=[2, 3])

    screen.insert_lines(2)

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["   ", "   ", "sam", "   ", "foo"]
    assert tolist(screen) == [
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [Char("s"), Char("a"), Char("m")],
        [screen.default_char] * 3,
        [Char("f", fg="red"), Char("o", fg="red"), Char("o", fg="red")],
    ]
    consistency_asserts(screen)

    screen.insert_lines(1)

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["   ", "   ", "   ", "sam", "   "]
    assert tolist(screen) == [
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [Char("s"), Char("a"), Char("m")],
        [screen.default_char] * 3,
    ]
    consistency_asserts(screen)

    screen.insert_lines(1)

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["   ", "   ", "   ", "   ", "sam"]
    assert tolist(screen) == [
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [Char("s"), Char("a"), Char("m")],
    ]
    consistency_asserts(screen)

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
    consistency_asserts(screen)

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
    consistency_asserts(screen)

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
    consistency_asserts(screen)

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
    consistency_asserts(screen)

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
    consistency_asserts(screen)


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
    consistency_asserts(screen)

    screen.delete_lines(0)

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["foo", "   ", "   "]
    assert tolist(screen) == [
        [Char("f"), Char("o"), Char("o")],
        [screen.default_char] * 3,
        [screen.default_char] * 3,
    ]
    consistency_asserts(screen)

    screen.delete_lines(0)

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["   ", "   ", "   "]
    assert tolist(screen) == [
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [screen.default_char] * 3,
    ]
    consistency_asserts(screen)

    screen.delete_lines(0)

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["   ", "   ", "   "]
    assert tolist(screen) == [
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [screen.default_char] * 3,
    ]
    consistency_asserts(screen)

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
    consistency_asserts(screen)

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
    consistency_asserts(screen)

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
    consistency_asserts(screen)

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
    consistency_asserts(screen)


def test_insert_characters():
    screen = update(pyte.Screen(3, 4), ["sam", "is ", "foo", "bar"],
                    colored=[0])

    # a) normal case
    cursor = copy.copy(screen.cursor)
    screen.insert_characters(2)
    assert (screen.cursor.y, screen.cursor.x) == (cursor.y, cursor.x)
    assert screen.display == ["  s", "is ", "foo", "bar"]
    assert tolist(screen)[0] == [
        screen.default_char,
        screen.default_char,
        Char("s", fg="red")
    ]
    consistency_asserts(screen)

    # b) now inserting from the middle of the line
    screen.cursor.y, screen.cursor.x = 2, 1
    screen.insert_characters(1)
    assert screen.display == ["  s", "is ", "f o", "bar"]
    assert tolist(screen)[2] == [Char("f"), screen.default_char, Char("o")]
    consistency_asserts(screen)

    # c) inserting more than we have
    screen.cursor.y, screen.cursor.x = 3, 1
    screen.insert_characters(10)
    assert screen.display == ["  s", "is ", "f o", "b  "]
    assert tolist(screen)[3] == [
        Char("b"), screen.default_char, screen.default_char
    ]

    assert screen.display == ["  s", "is ", "f o", "b  "]
    consistency_asserts(screen)

    # insert 1 at the begin of the previously edited line
    screen.cursor.y, screen.cursor.x = 3, 0
    screen.insert_characters(1)
    assert tolist(screen)[3] == [
        screen.default_char, Char("b"), screen.default_char,
    ]
    consistency_asserts(screen)

    # insert before the end of the line
    screen.cursor.y, screen.cursor.x = 3, 2
    screen.insert_characters(1)
    assert tolist(screen)[3] == [
        screen.default_char, Char("b"), screen.default_char,
    ]
    consistency_asserts(screen)

    # insert enough to push outside the screen the remaining char
    screen.cursor.y, screen.cursor.x = 3, 0
    screen.insert_characters(2)
    assert tolist(screen)[3] == [
        screen.default_char, screen.default_char, screen.default_char,
    ]

    assert screen.display == ["  s", "is ", "f o", "   "]
    consistency_asserts(screen)

    # d) 0 is 1
    screen = update(pyte.Screen(3, 3), ["sam", "is ", "foo"], colored=[0])

    screen.cursor_position()
    screen.insert_characters()
    assert tolist(screen)[0] == [
        screen.default_char,
        Char("s", fg="red"), Char("a", fg="red")
    ]
    consistency_asserts(screen)

    screen = update(pyte.Screen(3, 3), ["sam", "is ", "foo"], colored=[0])
    screen.cursor_position()
    screen.insert_characters(1)
    assert tolist(screen)[0] == [
        screen.default_char,
        Char("s", fg="red"), Char("a", fg="red")
    ]
    consistency_asserts(screen)


    # ! extreme cases.
    screen = update(pyte.Screen(5, 1), ["12345"], colored=[0])
    screen.cursor.x = 1
    screen.insert_characters(3)
    assert (screen.cursor.y, screen.cursor.x) == (0, 1)
    assert screen.display == ["1   2"]
    assert tolist(screen)[0] == [
        Char("1", fg="red"),
        screen.default_char,
        screen.default_char,
        screen.default_char,
        Char("2", fg="red"),
    ]
    consistency_asserts(screen)

    screen.insert_characters(1)
    assert (screen.cursor.y, screen.cursor.x) == (0, 1)
    assert screen.display == ["1    "]
    assert tolist(screen)[0] == [
        Char("1", fg="red"),
        screen.default_char,
        screen.default_char,
        screen.default_char,
        screen.default_char,
    ]
    consistency_asserts(screen)

    screen.cursor.x = 0
    screen.insert_characters(5)
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["     "]
    assert tolist(screen)[0] == [
        screen.default_char,
        screen.default_char,
        screen.default_char,
        screen.default_char,
        screen.default_char,
    ]
    consistency_asserts(screen)

def test_delete_characters():
    screen = update(pyte.Screen(3, 3), ["sam", "is ", "foo"], colored=[0])
    screen.delete_characters(2)
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["m  ", "is ", "foo"]
    assert tolist(screen)[0] == [
        Char("m", fg="red"),
        screen.default_char, screen.default_char
    ]
    consistency_asserts(screen)

    screen.cursor.y, screen.cursor.x = 2, 2
    screen.delete_characters()
    assert (screen.cursor.y, screen.cursor.x) == (2, 2)
    assert screen.display == ["m  ", "is ", "fo "]
    consistency_asserts(screen)

    screen.cursor.y, screen.cursor.x = 1, 1
    screen.delete_characters(0)
    assert (screen.cursor.y, screen.cursor.x) == (1, 1)
    assert screen.display == ["m  ", "i  ", "fo "]
    consistency_asserts(screen)

    # try to erase spaces
    screen.cursor.y, screen.cursor.x = 1, 1
    screen.delete_characters(0)
    assert (screen.cursor.y, screen.cursor.x) == (1, 1)
    assert screen.display == ["m  ", "i  ", "fo "]
    consistency_asserts(screen)

    # try to erase a whole line
    screen.cursor.y, screen.cursor.x = 1, 0
    screen.delete_characters(0)
    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["m  ", "   ", "fo "]
    consistency_asserts(screen)

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
    consistency_asserts(screen)

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
    consistency_asserts(screen)

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
    consistency_asserts(screen)

    screen.delete_characters(2)
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["     "]
    assert tolist(screen)[0] == [
        screen.default_char,
        screen.default_char,
        screen.default_char,
        screen.default_char,
        screen.default_char
    ]
    consistency_asserts(screen)


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
    consistency_asserts(screen)

    screen.cursor.y, screen.cursor.x = 2, 2
    screen.erase_characters()
    assert (screen.cursor.y, screen.cursor.x) == (2, 2)
    assert screen.display == ["  m", "is ", "fo "]
    consistency_asserts(screen)

    screen.cursor.y, screen.cursor.x = 1, 1
    screen.erase_characters(0)
    assert (screen.cursor.y, screen.cursor.x) == (1, 1)
    assert screen.display == ["  m", "i  ", "fo "]
    consistency_asserts(screen)

    # erase the same erased char as before
    screen.cursor.y, screen.cursor.x = 1, 1
    screen.erase_characters(0)
    assert (screen.cursor.y, screen.cursor.x) == (1, 1)
    assert screen.display == ["  m", "i  ", "fo "]
    consistency_asserts(screen)

    # erase the whole line
    screen.cursor.y, screen.cursor.x = 1, 0
    screen.erase_characters(0)
    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["  m", "   ", "fo "]
    consistency_asserts(screen)

    # erase 2 chars of an already-empty line with a cursor having a different
    # attribute
    screen.select_graphic_rendition(31) # red foreground
    screen.cursor.y, screen.cursor.x = 1, 0
    screen.erase_characters(2)
    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["  m", "   ", "fo "]
    assert tolist(screen)[1] == [
        Char(" ", fg='red'),
        Char(" ", fg='red'),
        screen.default_char
    ]
    consistency_asserts(screen)

    # erase 1 chars of a non-empty line with a cursor having a different
    # attribute
    screen.cursor.y, screen.cursor.x = 2, 1
    screen.erase_characters(1)
    assert (screen.cursor.y, screen.cursor.x) == (2, 1)
    assert screen.display == ["  m", "   ", "f  "]
    assert tolist(screen)[2] == [
        Char("f"),
        Char(" ", fg='red'),
        screen.default_char
    ]
    consistency_asserts(screen)

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
    consistency_asserts(screen)

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
    consistency_asserts(screen)

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
    consistency_asserts(screen)

    screen.cursor.x = 2
    screen.erase_characters(4)
    assert (screen.cursor.y, screen.cursor.x) == (0, 2)
    assert screen.display == ["     "]
    assert tolist(screen)[0] == [
        screen.default_char,
        screen.default_char,
        screen.default_char,
        screen.default_char,
        screen.default_char,
    ]
    consistency_asserts(screen)

def test_erase_in_line():
    screen = update(pyte.Screen(5, 5),
                    ["sam i",
                     "s foo",
                     "but a",
                     "re yo",
                     "u?   "], colored=[0, 1])
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
    consistency_asserts(screen)

    # erase from cursor to the end of line (again, same place)
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
    consistency_asserts(screen)

    # erase from cursor to the end of line (again but from the middle of a line))
    screen.cursor.y = 1
    screen.erase_in_line(0)
    assert (screen.cursor.y, screen.cursor.x) == (1, 2)
    assert screen.display == ["sa   ",
                              "s    ",
                              "but a",
                              "re yo",
                              "u?   "]
    assert tolist(screen)[1] == [
        Char("s", fg="red"),
        Char(" ", fg="red"), # this space comes from the setup, not from the erase
        screen.default_char,
        screen.default_char,
        screen.default_char
    ]
    consistency_asserts(screen)

    # erase from cursor to the end of line erasing the whole line
    screen.cursor.x = 0
    screen.erase_in_line(0)
    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["sa   ",
                              "     ",
                              "but a",
                              "re yo",
                              "u?   "]
    assert tolist(screen)[1] == [
        screen.default_char,
        screen.default_char,
        screen.default_char,
        screen.default_char,
        screen.default_char
    ]
    consistency_asserts(screen)

    # b) erase from the beginning of the line to the cursor
    screen = update(screen,
                    ["sam i",
                     "s foo",
                     "but a",
                     "re yo",
                     "u?   "], colored=[0])
    screen.cursor.x = 2
    screen.cursor.y = 0
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
    consistency_asserts(screen)

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
    consistency_asserts(screen)

    # d) erase with a non-default attributes cursor
    screen.select_graphic_rendition(31) # red foreground

    screen.cursor.y = 1
    screen.erase_in_line(2)
    assert (screen.cursor.y, screen.cursor.x) == (1, 2)
    assert screen.display == ["     ",
                              "     ",
                              "but a",
                              "re yo",
                              "u?   "]
    assert tolist(screen)[1] == [Char(" ", fg="red")] * 5
    consistency_asserts(screen)

    screen.cursor.y = 2
    screen.erase_in_line(1)
    assert (screen.cursor.y, screen.cursor.x) == (2, 2)
    assert screen.display == ["     ",
                              "     ",
                              "    a",
                              "re yo",
                              "u?   "]
    assert tolist(screen)[2] == [
            Char(" ", fg="red"),
            Char(" ", fg="red"),
            Char(" ", fg="red"),
            screen.default_char,
            Char("a"),
            ]

    consistency_asserts(screen)

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
    consistency_asserts(screen)

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
    consistency_asserts(screen)

    # c) erase the while display
    screen.erase_in_display(2)
    assert (screen.cursor.y, screen.cursor.x) == (2, 2)
    assert screen.display == ["     ",
                              "     ",
                              "     ",
                              "     ",
                              "     "]
    assert tolist(screen) == [[screen.default_char] * 5] * 5
    consistency_asserts(screen)

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
    consistency_asserts(screen)

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
    consistency_asserts(screen)

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
    consistency_asserts(screen)

    # erase from the beginning of the display to the cursor,
    # including it, but with the cursor having a non-default attribute
    screen = update(screen,
                    ["sam i",
                     "s foo",
                     "but a",
                     "re yo",
                     "u?   "], colored=[2, 3])

    screen.cursor.x = 2
    screen.cursor.y = 2
    screen.select_graphic_rendition(31) # red foreground
    screen.erase_in_display(1)
    assert (screen.cursor.y, screen.cursor.x) == (2, 2)
    assert screen.display == ["     ",
                              "     ",
                              "    a",
                              "re yo",
                              "u?   "]
    assert tolist(screen)[:3] == [
        [Char(" ", fg="red")] * 5,
        [Char(" ", fg="red")] * 5,
        [Char(" ", fg="red"),
         Char(" ", fg="red"),
         Char(" ", fg="red"),
         Char(" ", fg="red"),
         Char("a", fg="red")],
    ]
    consistency_asserts(screen)

    screen.erase_in_display(3)
    assert (screen.cursor.y, screen.cursor.x) == (2, 2)
    assert screen.display == ["     ",
                              "     ",
                              "     ",
                              "     ",
                              "     "]
    assert tolist(screen) == [
        [Char(" ", fg="red")] * 5,
        [Char(" ", fg="red")] * 5,
        [Char(" ", fg="red")] * 5,
        [Char(" ", fg="red")] * 5,
        [Char(" ", fg="red")] * 5,
    ]
    consistency_asserts(screen)

    # erase a clean screen (reset) from the begin to cursor
    screen.reset()
    screen.cursor.y = 2
    screen.cursor.x = 2
    screen.select_graphic_rendition(31) # red foreground

    screen.erase_in_display(1)
    assert (screen.cursor.y, screen.cursor.x) == (2, 2)
    assert screen.display == ["     ",
                              "     ",
                              "     ",
                              "     ",
                              "     "]
    assert tolist(screen) == [
        [Char(" ", fg="red")] * 5,
        [Char(" ", fg="red")] * 5,
        [Char(" ", fg="red")] * 3 + [screen.default_char] * 2,
        [screen.default_char] * 5,
        [screen.default_char] * 5,
    ]
    consistency_asserts(screen)

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
    consistency_asserts(screen)


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

    stream.feed("тест".encode("utf-8"))
    assert screen.display == ["тест", "    "]
    consistency_asserts(screen)


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
    consistency_asserts(screen)

    screen.alignment_display()

    assert screen.display == ["EEEEE",
                              "EEEEE",
                              "EEEEE",
                              "EEEEE",
                              "EEEEE"]
    consistency_asserts(screen)


def test_set_margins():
    screen = pyte.Screen(10, 10)

    assert screen.margins == (0, 9)

    # a) ok-case
    screen.set_margins(1, 5)
    assert screen.margins == (0, 4)

    # b) one of the margins is out of bounds
    screen.set_margins(100, 10)
    assert screen.margins != (99, 9)
    assert screen.margins == (0, 4)

    # c) no margins provided -- reset to full screen.
    screen.set_margins()
    assert screen.margins == (0, 9)


def test_set_margins_zero():
    # See https://github.com/selectel/pyte/issues/61
    screen = pyte.Screen(80, 24)
    screen.set_margins(1, 5)
    assert screen.margins == (0, 4)
    screen.set_margins(0)
    assert screen.margins == (0, 23)


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
    assert acc.pop() == ctrl.CSI + "{0};{1}R".format(1, 5)

    # d) cursor position, DECOM on
    screen.cursor_position()
    screen.set_margins(5, 9)
    screen.set_mode(mo.DECOM)
    screen.cursor_to_line(5)
    screen.report_device_status(6)
    assert acc.pop() == ctrl.CSI + "{0};{1}R".format(5, 1)


def test_screen_set_icon_name_title():
    screen = pyte.Screen(10, 1)

    text = "±"
    screen.set_icon_name(text)
    assert screen.icon_name == text

    screen.set_title(text)
    assert screen.title == text


def test_fuzzy_insert_characters():
    columns = 7

    # test different one-line screen scenarios with a mix
    # of empty and non-empty chars
    for mask in itertools.product('x ', repeat=columns):
        # make each 'x' a different letter so we can spot subtle errors
        line = [c if m == 'x' else ' ' for m, c in zip(mask, 'ABCDEFGHIJK')]
        assert len(line) == columns
        original = list(line)
        for count in [1, 2, columns//2, columns-1, columns, columns+1]:
            for at in [0, 1, columns//2, columns-count, columns-count+1, columns-1]:
                if at < 0:
                    continue

                for margins in [None, (1, columns-2)]:
                    screen = update(pyte.Screen(columns, 1), [line], write_spaces=False)

                    if margins:
                        # set_margins is 1-based indexes
                        screen.set_margins(top=margins[0]+1, bottom=margins[1]+1)

                    screen.cursor.x = at
                    screen.insert_characters(count)

                    # screen.insert_characters are not margins-aware so they
                    # will ignore any margin set. Therefore the expected
                    # line should also ignore them
                    expected_line = splice(line, at, count, [" "], margins=None)
                    expected_line = ''.join(expected_line)

                    assert screen.display == [expected_line], "At {}, cnt {}, (m {}), initial line: {}".format(at, count, margins, line)
                    consistency_asserts(screen)

                    # map the chars to Char objects
                    expected_line = [screen.default_char if c == ' ' else Char(c) for c in expected_line]
                    assert tolist(screen)[0] == expected_line, "At {}, cnt {}, (m {}), initial line: {}".format(at, count, margins, line)

        # ensure that the line that we used for the tests was not modified
        # so the tests used the correct line object (otherwise the tests
        # are invalid)
        assert original == line



def test_fuzzy_delete_characters():
    columns = 7

    # test different one-line screen scenarios with a mix
    # of empty and non-empty chars
    for mask in itertools.product('x ', repeat=columns):
        line = [c if m == 'x' else ' ' for m, c in zip(mask, 'ABCDEFGHIJK')]
        assert len(line) == columns
        original = list(line)
        for count in [1, 2, columns//2, columns-1, columns, columns+1]:
            for at in [0, 1, columns//2, columns-count, columns-count+1, columns-1]:
                if at < 0:
                    continue
                for margins in [None, (1, columns-2)]:
                    screen = update(pyte.Screen(columns, 1), [line], write_spaces=False)

                    if margins:
                        # set_margins is 1-based indexes
                        screen.set_margins(top=margins[0]+1, bottom=margins[1]+1)

                    screen.cursor.x = at
                    screen.delete_characters(count)

                    # screen.delete_characters are not margins-aware so they
                    # will ignore any margin set. Therefore the expected
                    # line should also ignore them
                    expected_line = splice(line, at, (-1)*count, [" "], margins=None)
                    expected_line = ''.join(expected_line)

                    assert screen.display == [expected_line], "At {}, cnt {}, (m {}), initial line: {}".format(at, count, margins, line)
                    consistency_asserts(screen)

                    # map the chars to Char objects
                    expected_line = [screen.default_char if c == ' ' else Char(c) for c in expected_line]
                    assert tolist(screen)[0] == expected_line, "At {}, cnt {}, (m {}), initial line: {}".format(at, count, margins, line)

        # ensure that the line that we used for the tests was not modified
        # so the tests used the correct line object (otherwise the tests
        # are invalid)
        assert original == line




def test_fuzzy_erase_characters():
    columns = 7

    # test different one-line screen scenarios with a mix
    # of empty and non-empty chars
    for mask in itertools.product('x ', repeat=columns):
        line = [c if m == 'x' else ' ' for m, c in zip(mask, 'ABCDEFGHIJK')]
        assert len(line) == columns
        original = list(line)
        for count in [1, 2, columns//2, columns-1, columns, columns+1]:
            for at in [0, 1, columns//2, columns-count, columns-count+1, columns-1]:
                if at < 0:
                    continue
                for margins in [None, (1, columns-2)]:
                    screen = update(pyte.Screen(columns, 1), [line], write_spaces=False)

                    if margins:
                        # set_margins is 1-based indexes
                        screen.set_margins(top=margins[0]+1, bottom=margins[1]+1)

                    screen.cursor.x = at
                    screen.erase_characters(count)

                    expected_line = list(line)
                    expected_line[at:at+count] = [" "] * (min(at+count, columns) - at)
                    expected_line = ''.join(expected_line)

                    assert screen.display == [expected_line], "At {}, cnt {}, (m {}), initial line: {}".format(at, count, margins, line)
                    consistency_asserts(screen)

                    # map the chars to Char objects
                    expected_line = [screen.default_char if c == ' ' else Char(c) for c in expected_line]
                    assert tolist(screen)[0] == expected_line, "At {}, cnt {}, (m {}), initial line: {}".format(at, count, margins, line)

        # ensure that the line that we used for the tests was not modified
        # so the tests used the correct line object (otherwise the tests
        # are invalid)
        assert original == line


def test_fuzzy_insert_lines():
    rows = 7

    # test different screen scenarios with a mix
    # of empty and non-empty lines
    for masks in itertools.product(['x x', '   '], repeat=rows):
        # make each line different
        lines = [m if m == '   ' else '%c %c' % (c,c) for m, c in zip(masks, "ABCDEFGHIJK")]
        assert len(lines) == rows
        original = list(lines)
        for count in [1, 2, rows//2, rows-1, rows, rows+1]:
            for at in [0, 1, rows//2, rows-count, rows-count+1, rows-1]:
                if at < 0:
                    continue
                for margins in [None, (1, rows-2)]:
                    screen = update(pyte.Screen(3, rows), lines, write_spaces=False)

                    if margins:
                        # set_margins is 1-based indexes
                        screen.set_margins(top=margins[0]+1, bottom=margins[1]+1)

                    screen.cursor.y = at
                    screen.insert_lines(count)

                    expected_lines = splice(lines, at, count, ["   "], margins)

                    assert screen.display == expected_lines, "At {}, cnt {}, (m {}), initial lines: {}".format(at, count, margins, lines)
                    consistency_asserts(screen)

                    # map the chars to Char objects
                    expected_lines = [[screen.default_char if c == ' ' else Char(c) for c in l] for l in expected_lines]
                    assert tolist(screen) == expected_lines, "At {}, cnt {}, (m {}), initial lines: {}".format(at, count, margins, lines)

        # ensure that the line that we used for the tests was not modified
        # so the tests used the correct line object (otherwise the tests
        # are invalid)
        assert original == lines



def test_fuzzy_delete_lines():
    rows = 7

    # test different screen scenarios with a mix
    # of empty and non-empty lines
    for masks in itertools.product(['x x', '   '], repeat=rows):
        lines = [m if m == '   ' else '%c %c' % (c,c) for m, c in zip(masks, "ABCDEFGHIJK")]
        assert len(lines) == rows
        original = list(lines)
        for count in [1, 2, rows//2, rows-1, rows, rows+1]:
            for at in [0, 1, rows//2, rows-count, rows-count+1, rows-1]:
                if at < 0:
                    continue
                for margins in [None, (1, rows-2)]:
                    screen = update(pyte.Screen(3, rows), lines, write_spaces=False)

                    if margins:
                        # set_margins is 1-based indexes
                        screen.set_margins(top=margins[0]+1, bottom=margins[1]+1)

                    screen.cursor.y = at
                    screen.delete_lines(count)

                    expected_lines = splice(lines, at, (-1)*count, ["   "], margins)

                    assert screen.display == expected_lines, "At {}, cnt {}, (m {}), initial lines: {}".format(at, count, margins, lines)
                    consistency_asserts(screen)

                    # map the chars to Char objects
                    expected_lines = [[screen.default_char if c == ' ' else Char(c) for c in l] for l in expected_lines]
                    assert tolist(screen) == expected_lines, "At {}, cnt {}, (m {}), initial lines: {}".format(at, count, margins, lines)

        # ensure that the line that we used for the tests was not modified
        # so the tests used the correct line object (otherwise the tests
        # are invalid)
        assert original == lines


def test_compressed_display():
    screen = update(pyte.Screen(4, 5), [
        "    ",
        " a  ",
        "    ",
        "  bb",
        "    ",
        ], write_spaces=False)

    assert screen.display == [
        "    ",
        " a  ",
        "    ",
        "  bb",
        "    ",
        ]

    assert screen.compressed_display() == [
        "    ",
        " a  ",
        "    ",
        "  bb",
        "    ",
        ]

    assert screen.compressed_display(lstrip=True) == [
        "",
        "a  ",
        "",
        "bb",
        "",
        ]

    assert screen.compressed_display(rstrip=True) == [
        "",
        " a",
        "",
        "  bb",
        "",
        ]

    assert screen.compressed_display(lstrip=True, rstrip=True) == [
        "",
        "a",
        "",
        "bb",
        "",
        ]

    assert screen.compressed_display(tfilter=True) == [
        " a  ",
        "    ",
        "  bb",
        "    ",
        ]

    assert screen.compressed_display(bfilter=True) == [
        "    ",
        " a  ",
        "    ",
        "  bb",
        ]

    assert screen.compressed_display(tfilter=True, bfilter=True) == [
        " a  ",
        "    ",
        "  bb",
        ]

    assert screen.compressed_display(tfilter=True, bfilter=True, rstrip=True) == [
        " a",
        "",
        "  bb",
        ]

    assert screen.compressed_display(tfilter=True, bfilter=True, lstrip=True) == [
        "a  ",
        "",
        "bb",
        ]
