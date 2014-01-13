# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import copy
import sys

if sys.version_info[0] == 2:
    from future_builtins import map
    str = unicode

import pytest

from pyte import Screen, Stream, mo
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


# Tests.

def test_remove_non_existant_attribute():
    screen = Screen(2, 2)
    assert screen.buffer == [[screen.default_char, screen.default_char]] * 2

    screen.select_graphic_rendition(24)  # underline-off.
    assert screen.buffer == [[screen.default_char, screen.default_char]] * 2
    assert not screen.cursor.attrs.underscore


def test_attributes():
    screen = Screen(2, 2)
    assert screen.buffer == [[screen.default_char, screen.default_char]] * 2
    screen.select_graphic_rendition(1) # Bold

    # Still default, since we haven't written anything.
    assert screen.buffer == [[screen.default_char, screen.default_char]] * 2
    assert screen.cursor.attrs.bold

    screen.draw("f")
    assert screen.buffer == [
        [Char("f", "default", "default", bold=True), screen.default_char],
        [screen.default_char, screen.default_char]
    ]


def test_colors():
    screen = Screen(2, 2)
    assert screen.buffer == [[screen.default_char, screen.default_char]] * 2

    screen.select_graphic_rendition(30) # black foreground
    screen.select_graphic_rendition(40) # black background
    assert screen.cursor.attrs.fg == "black"
    assert screen.cursor.attrs.bg == "black"

    screen.select_graphic_rendition(31) # red foreground
    assert screen.cursor.attrs.fg == "red"
    assert screen.cursor.attrs.bg == "black"


def test_reset_resets_colors():
    screen = Screen(2, 2)
    assert screen.buffer == [[screen.default_char, screen.default_char]] * 2

    screen.select_graphic_rendition(30)
    screen.select_graphic_rendition(40)
    assert screen.cursor.attrs.fg == "black"
    assert screen.cursor.attrs.bg == "black"

    screen.select_graphic_rendition(0)
    assert screen.cursor.attrs == screen.default_char


def test_multi_attribs():
    screen = Screen(2, 2)
    assert screen.buffer == [[screen.default_char, screen.default_char]] * 2
    screen.select_graphic_rendition(1)
    screen.select_graphic_rendition(3)

    assert screen.cursor.attrs.bold
    assert screen.cursor.attrs.italics


def test_attributes_reset():
    screen = Screen(2, 2)
    screen.set_mode(mo.LNM)
    assert screen.buffer == [[screen.default_char, screen.default_char]] * 2
    screen.select_graphic_rendition(1)
    screen.draw("f")
    screen.draw("o")
    screen.draw("o")
    assert screen.buffer == [
        [Char("f", bold=True), Char("o", bold=True)],
        [Char("o", bold=True), screen.default_char  ],
    ]

    screen.cursor_position()
    screen.select_graphic_rendition(0) # Reset
    screen.draw("f")
    assert screen.buffer == [
        [Char("f"),            Char("o", bold=True)],
        [Char("o", bold=True), screen.default_char  ],
    ]


def test_resize():
    screen = Screen(2, 2)
    screen.set_mode(mo.DECOM)
    screen.set_margins(0, 1)
    assert screen.size == (2, 2)
    assert screen.columns == 2
    assert len(screen.buffer[0]) == 2
    assert screen.buffer == [[screen.default_char, screen.default_char]] * 2

    screen.resize(3, 3)
    assert screen.size == (3, 3)
    assert len(screen.buffer) == 3
    assert len(screen.buffer[0]) == 3
    assert screen.buffer == [[screen.default_char,
                       screen.default_char,
                       screen.default_char]] * 3
    assert mo.DECOM not in screen.mode
    assert screen.margins == (0, 2)


    screen.resize(2, 2)
    assert screen.size == (2, 2)
    assert len(screen.buffer) == 2
    assert len(screen.buffer[0]) == 2
    assert screen.buffer == [[screen.default_char, screen.default_char]] * 2


    # quirks:
    # a) if the current display is thinner than the requested size,
    #    new columns should be added to the right.
    screen = update(Screen(2, 2), ["bo", "sh"], [None, None])
    screen.resize(2, 3)
    assert screen.display == ["bo ", "sh "]

    # b) if the current display is wider than the requested size,
    #    columns should be removed from the right...
    screen = update(Screen(2, 2), ["bo", "sh"], [None, None])
    screen.resize(2, 1)
    assert screen.display == ["b", "s"]

    # c) if the current display is shorter than the requested
    #    size, new rows should be added on the bottom.
    screen = update(Screen(2, 2), ["bo", "sh"], [None, None])
    screen.resize(3, 2)

    assert screen.display == ["bo", "sh", "  "]

    # d) if the current display is taller than the requested
    #    size, rows should be removed from the top.
    screen = update(Screen(2, 2), ["bo", "sh"], [None, None])
    screen.resize(1, 2)
    assert screen.display == ["sh"]


def test_draw():
    # ``DECAWM`` on (default).
    screen = Screen(3, 3)
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
    screen = Screen(3, 3)
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


def test_carriage_return():
    screen = Screen(3, 3)
    screen.cursor.x = 2
    screen.carriage_return()

    assert screen.cursor.x == 0


def test_index():
    screen = update(Screen(2, 2), ["wo", "ot"], colored=[1])

    # a) indexing on a row that isn't the last should just move
    # the cursor down.
    screen.index()
    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.buffer == [
        [Char("w"), Char("o")],
        [Char("o", fg="red"), Char("t", fg="red")]
    ]

    # b) indexing on the last row should push everything up and
    # create a new row at the bottom.
    screen.index()
    assert screen.cursor.y == 1
    assert screen.buffer == [
        [Char("o", fg="red"), Char("t", fg="red")],
        [screen.default_char, screen.default_char]
    ]

    # c) same with margins
    screen = update(Screen(2, 5), ["bo", "sh", "th", "er", "oh"],
                    colored=[1, 2])
    screen.set_margins(2, 4)
    screen.cursor.y = 3

    # ... go!
    screen.index()
    assert (screen.cursor.y, screen.cursor.x) == (3, 0)
    assert screen.display == ["bo", "th", "er", "  ", "oh"]
    assert screen.buffer == [
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
    assert screen.buffer == [
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
    assert screen.buffer == [
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
    assert screen.buffer == [
        [Char("b"), Char("o")],
        [screen.default_char, screen.default_char],
        [screen.default_char, screen.default_char],
        [screen.default_char, screen.default_char],
        [Char("o"), Char("h")],
    ]


def test_reverse_index():
    screen = update(Screen(2, 2), ["wo", "ot"], colored=[0])

    # a) reverse indexing on the first row should push rows down
    # and create a new row at the top.
    screen.reverse_index()
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.buffer == [
        [screen.default_char, screen.default_char],
        [Char("w", fg="red"), Char("o", fg="red")]
    ]

    # b) once again ...
    screen.reverse_index()
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.buffer == [
        [screen.default_char, screen.default_char],
        [screen.default_char, screen.default_char],
    ]

    # c) same with margins
    screen = update(Screen(2, 5), ["bo", "sh", "th", "er", "oh"],
                    colored=[2, 3])
    screen.set_margins(2, 4)
    screen.cursor.y = 1

    # ... go!
    screen.reverse_index()
    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["bo", "  ", "sh", "th", "oh"]
    assert screen.buffer == [
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
    assert screen.buffer == [
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
    assert screen.buffer == [
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
    assert screen.buffer == [
        [Char("b"), Char("o")],
        [screen.default_char, screen.default_char],
        [screen.default_char, screen.default_char],
        [screen.default_char, screen.default_char],
        [Char("o"), Char("h")],
    ]


def test_linefeed():
    screen = update(Screen(2, 2), ["bo", "sh"], [None, None])
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


def test_tabstops():
    screen = Screen(10, 10)

    # Making sure initial tabstops are in place ...
    assert screen.tabstops == set([7])

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
    screen = Screen(10, 10)
    screen.clear_tab_stop(3)

    # a) clear a tabstop at current cusor location
    screen.cursor.x = 1
    screen.set_tab_stop()
    screen.cursor.x = 5
    screen.set_tab_stop()
    screen.clear_tab_stop()

    assert screen.tabstops == set([1])

    screen.set_tab_stop()
    screen.clear_tab_stop(0)

    assert screen.tabstops == set([1])

    # b) all tabstops
    screen.set_tab_stop()
    screen.cursor.x = 9
    screen.set_tab_stop()
    screen.clear_tab_stop(3)

    assert not screen.tabstops


def test_backspace():
    screen = Screen(2, 2)
    assert screen.cursor.x == 0
    screen.backspace()
    assert screen.cursor.x == 0
    screen.cursor.x = 1
    screen.backspace()
    assert screen.cursor.x == 0


def test_save_cursor():
    # a) cursor position
    screen = Screen(10, 10)
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
    screen = Screen(10, 10)
    screen.set_mode(mo.DECAWM, mo.DECOM)
    screen.save_cursor()

    screen.reset_mode(mo.DECAWM)

    screen.restore_cursor()
    assert mo.DECAWM in screen.mode
    assert mo.DECOM in screen.mode

    # c) attributes
    screen = Screen(10, 10)
    screen.select_graphic_rendition(4)
    screen.save_cursor()
    screen.select_graphic_rendition(24)

    assert screen.cursor.attrs == screen.default_char

    screen.restore_cursor()

    assert screen.cursor.attrs != screen.default_char
    assert screen.cursor.attrs == Char(" ", underscore=True)


def test_restore_cursor_with_none_saved():
    screen = Screen(10, 10)
    screen.set_mode(mo.DECOM)
    screen.cursor.x, screen.cursor.y = 5, 5
    screen.restore_cursor()

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert mo.DECOM not in screen.mode


def test_restore_cursor_out_of_bounds():
    screen = Screen(10, 10)

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
    screen = update(Screen(3, 3), ["sam", "is ", "foo"], colored=[1])
    screen.insert_lines()

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["   ", "sam", "is "]
    assert screen.buffer == [
        [screen.default_char] * 3,
        [Char("s"), Char("a"), Char("m")],
        [Char("i", fg="red"), Char("s", fg="red"), Char(" ", fg="red")],
    ]

    screen = update(Screen(3, 3), ["sam", "is ", "foo"], colored=[1])
    screen.insert_lines(2)

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["   ", "   ", "sam"]
    assert screen.buffer == [
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [Char("s"), Char("a"), Char("m")]
    ]

    # b) with margins
    screen = update(Screen(3, 5), ["sam", "is ", "foo", "bar", "baz"],
                    colored=[2, 3])
    screen.set_margins(1, 4)
    screen.cursor.y = 1
    screen.insert_lines(1)

    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["sam", "   ", "is ", "foo", "baz"]
    assert screen.buffer == [
        [Char("s"), Char("a"), Char("m")],
        [screen.default_char] * 3,
        [Char("i"), Char("s"), Char(" ")],
        [Char("f", fg="red"), Char("o", fg="red"), Char("o", fg="red")],
        [Char("b"), Char("a"), Char("z")],
    ]

    screen = update(Screen(3, 5), ["sam", "is ", "foo", "bar", "baz"],
                    colored=[2, 3])
    screen.set_margins(1, 3)
    screen.cursor.y = 1
    screen.insert_lines(1)

    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["sam", "   ", "is ", "bar",  "baz"]
    assert screen.buffer == [
        [Char("s"), Char("a"), Char("m")],
        [screen.default_char] * 3,
        [Char("i"), Char("s"), Char(" ")],
        [Char("b", fg="red"), Char("a", fg="red"), Char("r", fg="red")],
        [Char("b"), Char("a"), Char("z")],
    ]

    screen.insert_lines(2)
    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["sam", "   ", "   ", "bar",  "baz"]
    assert screen.buffer == [
        [Char("s"), Char("a"), Char("m")],
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [Char("b", fg="red"), Char("a", fg="red"), Char("r", fg="red")],
        [Char("b"), Char("a"), Char("z")],
    ]

    # c) with margins -- trying to insert more than we have available
    screen = update(Screen(3, 5), ["sam", "is ", "foo", "bar", "baz"],
                    colored=[2, 3])
    screen.set_margins(2, 4)
    screen.cursor.y = 1
    screen.insert_lines(20)

    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["sam", "   ", "   ", "   ", "baz"]
    assert screen.buffer == [
        [Char("s"), Char("a"), Char("m")],
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [Char("b"), Char("a"), Char("z")],
    ]

    # d) with margins -- trying to insert outside scroll boundaries;
    #    expecting nothing to change
    screen = update(Screen(3, 5), ["sam", "is ", "foo", "bar", "baz"],
                    colored=[2, 3])
    screen.set_margins(2, 4)
    screen.insert_lines(5)

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["sam", "is ", "foo", "bar", "baz"]
    assert screen.buffer == [
        [Char("s"), Char("a"), Char("m")],
        [Char("i"), Char("s"), Char(" ")],
        [Char("f", fg="red"), Char("o", fg="red"), Char("o", fg="red")],
        [Char("b", fg="red"), Char("a", fg="red"), Char("r", fg="red")],
        [Char("b"), Char("a"), Char("z")],
    ]


def test_delete_lines():
    # a) without margins
    screen = update(Screen(3, 3), ["sam", "is ", "foo"], colored=[1])
    screen.delete_lines()

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["is ", "foo", "   "]
    assert screen.buffer == [
        [Char("i", fg="red"), Char("s", fg="red"), Char(" ", fg="red")],
        [Char("f"), Char("o"), Char("o")],
        [screen.default_char] * 3,
    ]

    screen.delete_lines(0)

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["foo", "   ", "   "]
    assert screen.buffer == [
        [Char("f"), Char("o"), Char("o")],
        [screen.default_char] * 3,
        [screen.default_char] * 3,
    ]

    # b) with margins
    screen = update(Screen(3, 5), ["sam", "is ", "foo", "bar", "baz"],
                    colored=[2, 3])
    screen.set_margins(1, 4)
    screen.cursor.y = 1
    screen.delete_lines(1)

    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["sam", "foo", "bar", "   ", "baz"]
    assert screen.buffer == [
        [Char("s"), Char("a"), Char("m")],
        [Char("f", fg="red"), Char("o", fg="red"), Char("o", fg="red")],
        [Char("b", fg="red"), Char("a", fg="red"), Char("r", fg="red")],
        [screen.default_char] * 3,
        [Char("b"), Char("a"), Char("z")],
    ]

    screen = update(Screen(3, 5), ["sam", "is ", "foo", "bar", "baz"],
                    colored=[2, 3])
    screen.set_margins(1, 4)
    screen.cursor.y = 1
    screen.delete_lines(2)

    assert (screen.cursor.y, screen.cursor.x) == (1, 0)
    assert screen.display == ["sam", "bar", "   ", "   ", "baz"]
    assert screen.buffer == [
        [Char("s"), Char("a"), Char("m")],
        [Char("b", fg="red"), Char("a", fg="red"), Char("r", fg="red")],
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [Char("b"), Char("a"), Char("z")],
    ]

    # c) with margins -- trying to delete  more than we have available
    screen = update(Screen(3, 5),
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
    assert screen.buffer == [
        [Char("s"), Char("a"), Char("m")],
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [screen.default_char] * 3,
        [Char("b"), Char("a"), Char("z")],
    ]

    # d) with margins -- trying to delete outside scroll boundaries;
    #    expecting nothing to change
    screen = update(Screen(3, 5), ["sam", "is ", "foo", "bar", "baz"],
                    colored=[2, 3])
    screen.set_margins(2, 4)
    screen.cursor.y = 0
    screen.delete_lines(5)

    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["sam", "is ", "foo", "bar", "baz"]
    assert screen.buffer == [
        [Char("s"), Char("a"), Char("m")],
        [Char("i"), Char("s"), Char(" ")],
        [Char("f", fg="red"), Char("o", fg="red"), Char("o", fg="red")],
        [Char("b", fg="red"), Char("a", fg="red"), Char("r", fg="red")],
        [Char("b"), Char("a"), Char("z")],
    ]


def test_insert_characters():
    screen = update(Screen(3, 3), ["sam", "is ", "foo"], colored=[0])

    # a) normal case
    cursor = copy.copy(screen.cursor)
    screen.insert_characters(2)
    assert (screen.cursor.y, screen.cursor.x) == (cursor.y, cursor.x)
    assert screen.buffer[0] == [
        screen.default_char,
        screen.default_char,
        Char("s", fg="red")
    ]

    # b) now inserting from the middle of the line
    screen.cursor.y, screen.cursor.x = 2, 1
    screen.insert_characters(1)
    assert screen.buffer[2] == [Char("f"), screen.default_char, Char("o")]

    # c) inserting more than we have
    screen.insert_characters(10)
    assert screen.buffer[2] == [Char("f"), screen.default_char, screen.default_char]

    # d) 0 is 1
    screen = update(Screen(3, 3), ["sam", "is ", "foo"], colored=[0])

    screen.cursor_position()
    screen.insert_characters()
    assert screen.buffer[0] == [
        screen.default_char,
        Char("s", fg="red"), Char("a", fg="red")
    ]

    screen = update(Screen(3, 3), ["sam", "is ", "foo"], colored=[0])
    screen.cursor_position()
    screen.insert_characters(1)
    assert screen.buffer[0] == [
        screen.default_char,
        Char("s", fg="red"), Char("a", fg="red")
    ]


def test_delete_characters():
    screen = update(Screen(3, 3), ["sam", "is ", "foo"], colored=[0])
    screen.delete_characters(2)
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["m  ", "is ", "foo"]
    assert screen.buffer[0] == [
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
    screen = update(Screen(5, 1), ["12345"], colored=[0])
    screen.cursor.x = 1
    screen.delete_characters(3)
    assert (screen.cursor.y, screen.cursor.x) == (0, 1)
    assert screen.display == ["15   "]
    assert screen.buffer[0] == [
        Char("1", fg="red"),
        Char("5", fg="red"),
        screen.default_char,
        screen.default_char,
        screen.default_char
    ]

    screen = update(Screen(5, 1), ["12345"], colored=[0])
    screen.cursor.x = 2
    screen.delete_characters(10)
    assert (screen.cursor.y, screen.cursor.x) == (0, 2)
    assert screen.display == ["12   "]
    assert screen.buffer[0] == [
        Char("1", fg="red"),
        Char("2", fg="red"),
        screen.default_char,
        screen.default_char,
        screen.default_char
    ]

    screen = update(Screen(5, 1), ["12345"], colored=[0])
    screen.delete_characters(4)
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["5    "]
    assert screen.buffer[0] == [
        Char("5", fg="red"),
        screen.default_char,
        screen.default_char,
        screen.default_char,
        screen.default_char
    ]


def test_erase_character():
    screen = update(Screen(3, 3), ["sam", "is ", "foo"], colored=[0])

    screen.erase_characters(2)
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["  m", "is ", "foo"]
    assert screen.buffer[0] == [
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
    screen = update(Screen(5, 1), ["12345"], colored=[0])
    screen.cursor.x = 1
    screen.erase_characters(3)
    assert (screen.cursor.y, screen.cursor.x) == (0, 1)
    assert screen.display == ["1   5"]
    assert screen.buffer[0] == [
        Char("1", fg="red"),
        screen.default_char,
        screen.default_char,
        screen.default_char,
        Char("5", "red")
    ]

    screen = update(Screen(5, 1), ["12345"], colored=[0])
    screen.cursor.x = 2
    screen.erase_characters(10)
    assert (screen.cursor.y, screen.cursor.x) == (0, 2)
    assert screen.display == ["12   "]
    assert screen.buffer[0] == [
        Char("1", fg="red"),
        Char("2", fg="red"),
        screen.default_char,
        screen.default_char,
        screen.default_char
    ]

    screen = update(Screen(5, 1), ["12345"], colored=[0])
    screen.erase_characters(4)
    assert (screen.cursor.y, screen.cursor.x) == (0, 0)
    assert screen.display == ["    5"]
    assert screen.buffer[0] == [
        screen.default_char,
        screen.default_char,
        screen.default_char,
        screen.default_char,
        Char("5", fg="red")
    ]


def test_erase_in_line():
    screen = update(Screen(5, 5),
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
    assert screen.buffer[0] == [
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
    assert screen.buffer[0] == [
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
    assert screen.buffer[0] == [screen.default_char] * 5


def test_erase_in_display():
    screen = update(Screen(5, 5),
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
    assert screen.buffer[2:] == [
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
    assert screen.buffer[:3] == [
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
    assert screen.buffer == [[screen.default_char] * 5] * 5


def test_cursor_up():
    screen = Screen(10, 10)

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
    screen = Screen(10, 10)

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
    screen = Screen(10, 10)

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


def test_cursor_forward():
    screen = Screen(10, 10)

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
    screen = Screen(10, 10)

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
    screen = Screen(4, 2)
    stream = Stream()
    stream.attach(screen)

    try:
        stream.feed("тест")
    except UnicodeDecodeError:
        pytest.fail("Check your code -- we do accept unicode.")

    assert screen.display == ["тест", "    "]


def test_alignment_display():
    screen = Screen(5, 5)
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
    screen = Screen(10, 10)

    assert screen.margins == (0, 9)

    # a) ok-case
    screen.set_margins(1, 5)
    assert screen.margins == (0, 4)

    # b) one of the margins is out of bounds
    screen.set_margins(100, 10)
    assert screen.margins != (99, 9)
    assert screen.margins == (0, 4)

    # c) no margins provided
    screen.set_margins()
    assert screen.margins != (None, None)
    assert screen.margins == (0, 4)


def test_hide_cursor():
    screen = Screen(10, 10)

    # DECTCEM is set by default.
    assert mo.DECTCEM in screen.mode
    assert not screen.cursor.hidden

    # a) resetting DECTCEM hides the cursor.
    screen.reset_mode(mo.DECTCEM)
    assert screen.cursor.hidden

    # b) ... and it's back!
    screen.set_mode(mo.DECTCEM)
    assert not screen.cursor.hidden
