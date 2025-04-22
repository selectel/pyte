import os

import pyte
from pyte import control as ctrl, modes as mo


def chars(history_lines, columns):
    return ["".join(history_lines[y][x].data for x in range(columns))
            for y in range(len(history_lines))]


def test_index():
    screen = pyte.HistoryScreen(5, 5, history=50)

    # Filling the screen with line numbers, so it's easier to
    # track history contents.
    for idx in range(screen.lines):
        screen.draw(str(idx))
        if idx != screen.lines - 1:
            screen.linefeed()

    assert not screen.history.top
    assert not screen.history.bottom

    # a) first index, expecting top history to be updated.
    line = screen.buffer[0]
    screen.index()
    assert screen.history.top
    assert screen.history.top[-1] == line

    # b) second index.
    line = screen.buffer[0]
    screen.index()
    assert len(screen.history.top) == 2
    assert screen.history.top[-1] == line

    # c) rotation.
    for _ in range(screen.history.size * 2):
        screen.index()

    assert len(screen.history.top) == 50


def test_reverse_index():
    screen = pyte.HistoryScreen(5, 5, history=50)

    # Filling the screen with line numbers, so it's easier to
    # track history contents.
    for idx in range(len(screen.buffer)):
        screen.draw(str(idx))
        if idx != len(screen.buffer) - 1:
            screen.linefeed()

    assert not screen.history.top
    assert not screen.history.bottom

    screen.cursor_position()

    # a) first index, expecting top history to be updated.
    line = screen.buffer[-1]
    screen.reverse_index()
    assert screen.history.bottom
    assert screen.history.bottom[0] == line

    # b) second index.
    line = screen.buffer[-1]
    screen.reverse_index()
    assert len(screen.history.bottom) == 2
    assert screen.history.bottom[1] == line

    # c) rotation.
    for _ in range(len(screen.buffer) ** screen.lines):
        screen.reverse_index()

    assert len(screen.history.bottom) == 50


def test_prev_page():
    screen = pyte.HistoryScreen(4, 4, history=40)
    screen.set_mode(mo.LNM)

    assert screen.history.position == 40

    # Once again filling the screen with line numbers, but this time,
    # we need them to span on multiple lines.
    for idx in range(screen.lines * 10):
        screen.draw(str(idx))
        screen.linefeed()

    assert screen.history.top
    assert not screen.history.bottom
    assert screen.history.position == 40
    assert screen.display == [
        "37  ",
        "38  ",
        "39  ",
        "    "
    ]

    assert chars(screen.history.top, screen.columns)[-4:] == [
        "33  ",
        "34  ",
        "35  ",
        "36  "
    ]

    # a) first page up.
    screen.prev_page()
    assert screen.history.position == 38
    assert len(screen.buffer) == screen.lines
    assert screen.display == [
        "35  ",
        "36  ",
        "37  ",
        "38  "
    ]

    assert chars(screen.history.top, screen.columns)[-4:] == [
        "31  ",
        "32  ",
        "33  ",
        "34  "
    ]

    assert len(screen.history.bottom) == 2
    assert chars(screen.history.bottom, screen.columns) == [
        "39  ",
        "    ",
    ]

    # b) second page up.
    screen.prev_page()
    assert screen.history.position == 36
    assert len(screen.buffer) == screen.lines
    assert screen.display == [
        "33  ",
        "34  ",
        "35  ",
        "36  ",
    ]

    assert len(screen.history.bottom) == 4
    assert chars(screen.history.bottom, screen.columns) == [
        "37  ",
        "38  ",
        "39  ",
        "    ",
    ]

    # c) same with odd number of lines.
    screen = pyte.HistoryScreen(5, 5, history=50)
    screen.set_mode(mo.LNM)

    for idx in range(screen.lines * 10):
        screen.draw(str(idx))
        screen.linefeed()

    assert screen.history.top
    assert not screen.history.bottom
    assert screen.history.position == 50
    assert screen.display == [
        "46   ",
        "47   ",
        "48   ",
        "49   ",
        "     "
    ]

    screen.prev_page()
    assert screen.history.position == 47
    assert screen.display == [
        "43   ",
        "44   ",
        "45   ",
        "46   ",
        "47   "
    ]

    assert len(screen.history.bottom) == 3
    assert chars(screen.history.bottom, screen.columns) == [
        "48   ",
        "49   ",
        "     ",
    ]

    # d) with a ratio other than 0.5
    screen = pyte.HistoryScreen(4, 4, history=40, ratio=0.75)
    screen.set_mode(mo.LNM)

    for idx in range(screen.lines * 10):
        screen.draw(str(idx))
        screen.linefeed()

    assert screen.history.top
    assert not screen.history.bottom
    assert screen.history.position == 40
    assert screen.display == [
        "37  ",
        "38  ",
        "39  ",
        "    "
    ]

    screen.prev_page()
    assert screen.history.position == 37
    assert screen.display == [
        "34  ",
        "35  ",
        "36  ",
        "37  "
    ]

    assert len(screen.history.bottom) == 3
    assert chars(screen.history.bottom, screen.columns) == [
        "38  ",
        "39  ",
        "    "
    ]

    # e) same with cursor in the middle of the screen.
    screen = pyte.HistoryScreen(5, 5, history=50)
    screen.set_mode(mo.LNM)

    for idx in range(screen.lines * 10):
        screen.draw(str(idx))
        screen.linefeed()

    assert screen.history.top
    assert not screen.history.bottom
    assert screen.history.position == 50
    assert screen.display == [
        "46   ",
        "47   ",
        "48   ",
        "49   ",
        "     "
    ]

    screen.cursor_to_line(screen.lines // 2)

    while screen.history.position > screen.lines:
        screen.prev_page()

    assert screen.history.position == screen.lines
    assert len(screen.buffer) == screen.lines
    assert screen.display == [
        "1    ",
        "2    ",
        "3    ",
        "4    ",
        "5    "
    ]

    while screen.history.position < screen.history.size:
        screen.next_page()

    assert screen.history.position == screen.history.size
    assert screen.display == [
        "46   ",
        "47   ",
        "48   ",
        "49   ",
        "     "
    ]

    # e) same with cursor near the middle of the screen.
    screen = pyte.HistoryScreen(5, 5, history=50)
    screen.set_mode(mo.LNM)

    for idx in range(screen.lines * 10):
        screen.draw(str(idx))

        screen.linefeed()

    assert screen.history.top
    assert not screen.history.bottom
    assert screen.history.position == 50
    assert screen.display == [
        "46   ",
        "47   ",
        "48   ",
        "49   ",
        "     "
    ]

    screen.cursor_to_line(screen.lines // 2 - 2)

    while screen.history.position > screen.lines:
        screen.prev_page()

    assert screen.history.position == screen.lines
    assert len(screen.buffer) == screen.lines
    assert screen.display == [
        "1    ",
        "2    ",
        "3    ",
        "4    ",
        "5    "
    ]

    while screen.history.position < screen.history.size:
        screen.next_page()

    assert screen.history.position == screen.history.size
    assert len(screen.buffer) == screen.lines
    assert screen.display == [
        "46   ",
        "47   ",
        "48   ",
        "49   ",
        "     "
    ]


def test_next_page():
    screen = pyte.HistoryScreen(5, 5, history=50)
    screen.set_mode(mo.LNM)

    # Once again filling the screen with line numbers, but this time,
    # we need them to span on multiple lines.
    for idx in range(screen.lines * 5):
        screen.draw(str(idx))
        screen.linefeed()

    assert screen.history.top
    assert not screen.history.bottom
    assert screen.history.position == 50
    assert screen.display == [
        "21   ",
        "22   ",
        "23   ",
        "24   ",
        "     "
    ]

    # a) page up -- page down.
    screen.prev_page()
    screen.next_page()
    assert screen.history.top
    assert not screen.history.bottom
    assert screen.history.position == 50
    assert screen.display == [
        "21   ",
        "22   ",
        "23   ",
        "24   ",
        "     "
    ]

    # b) double page up -- page down.
    screen.prev_page()
    screen.prev_page()
    screen.next_page()
    assert screen.history.position == 47
    assert screen.history.top
    assert chars(screen.history.bottom, screen.columns) == [
        "23   ",
        "24   ",
        "     "
    ]

    assert screen.display == [
        "18   ",
        "19   ",
        "20   ",
        "21   ",
        "22   "
    ]

    # c) double page up -- double page down
    screen.prev_page()
    screen.prev_page()
    screen.next_page()
    screen.next_page()
    assert screen.history.position == 47
    assert len(screen.buffer) == screen.lines
    assert screen.display == [
        "18   ",
        "19   ",
        "20   ",
        "21   ",
        "22   "
    ]


def test_ensure_width(monkeypatch):
    screen = pyte.HistoryScreen(5, 5, history=50)
    screen.set_mode(mo.LNM)
    escape = dict(pyte.Stream.escape)
    escape.update({"N": "next_page", "P": "prev_page"})
    monkeypatch.setattr(pyte.Stream, "escape", escape)

    stream = pyte.Stream(screen)

    for idx in range(screen.lines * 5):
        stream.feed(f"{idx:04d}" + os.linesep)

    assert screen.display == [
        "0021 ",
        "0022 ",
        "0023 ",
        "0024 ",
        "     "
    ]

    # Shrinking the screen should truncate the displayed lines following lines.
    screen.resize(5, 3)
    stream.feed(ctrl.ESC + "P")

    # Inequality because we have an all-empty last line.
    assert all(len(l) <= 3 for l in screen.history.bottom)
    assert screen.display == [
        "001",  # 18
        "001",  # 19
        "002",  # 20
        "002",  # 21
        "002"   # 22
    ]


def test_not_enough_lines():
    screen = pyte.HistoryScreen(5, 5, history=6)
    screen.set_mode(mo.LNM)

    for idx in range(screen.lines):
        screen.draw(str(idx))
        screen.linefeed()

    assert screen.history.top
    assert not screen.history.bottom
    assert screen.history.position == 6
    assert screen.display == [
        "1    ",
        "2    ",
        "3    ",
        "4    ",
        "     "
    ]

    screen.prev_page()
    assert not screen.history.top
    assert len(screen.history.bottom) is 1
    assert chars(screen.history.bottom, screen.columns) == ["     "]
    assert screen.display == [
        "0    ",
        "1    ",
        "2    ",
        "3    ",
        "4    ",
    ]

    screen.next_page()
    assert screen.history.top
    assert not screen.history.bottom
    assert screen.display == [
        "1    ",
        "2    ",
        "3    ",
        "4    ",
        "     "
    ]


def test_draw(monkeypatch):
    screen = pyte.HistoryScreen(5, 5, history=50)
    screen.set_mode(mo.LNM)
    escape = dict(pyte.Stream.escape)
    escape.update({"N": "next_page", "P": "prev_page"})
    monkeypatch.setattr(pyte.Stream, "escape", escape)

    stream = pyte.Stream(screen)
    for idx in range(screen.lines * 5):
        stream.feed(str(idx) + os.linesep)

    assert screen.display == [
        "21   ",
        "22   ",
        "23   ",
        "24   ",
        "     "
    ]

    # a) doing a pageup and then a draw -- expecting the screen
    #    to scroll to the bottom before drawing anything.
    stream.feed(ctrl.ESC + "P")
    stream.feed(ctrl.ESC + "P")
    stream.feed(ctrl.ESC + "N")
    stream.feed("x")

    assert screen.display == [
        "21   ",
        "22   ",
        "23   ",
        "24   ",
        "x    "
    ]


def test_cursor_is_hidden(monkeypatch):
    screen = pyte.HistoryScreen(5, 5, history=50)
    escape = dict(pyte.Stream.escape)
    escape.update({"N": "next_page", "P": "prev_page"})
    monkeypatch.setattr(pyte.Stream, "escape", escape)

    stream = pyte.Stream(screen)
    for idx in range(screen.lines * 5):
        stream.feed(str(idx) + os.linesep)

    assert not screen.cursor.hidden

    stream.feed(ctrl.ESC + "P")
    assert screen.cursor.hidden
    stream.feed(ctrl.ESC + "P")
    assert screen.cursor.hidden
    stream.feed(ctrl.ESC + "N")
    assert screen.cursor.hidden
    stream.feed(ctrl.ESC + "N")
    assert not screen.cursor.hidden


def test_erase_in_display():
    screen = pyte.HistoryScreen(5, 5, history=6)
    screen.set_mode(mo.LNM)

    for idx in range(screen.lines):
        screen.draw(str(idx))
        screen.linefeed()

    screen.prev_page()

    # See #80 on GitHub for details.
    screen.erase_in_display(3)
    assert not screen.history.top
    assert not screen.history.bottom
