import pyte
from pyte import modes as mo


def test_mark_whole_screen():
    # .. this is straightforward -- make sure we have a dirty attribute
    # and whole screen is marked as dirty on initialization, reset,
    # resize etc.
    screen = pyte.DiffScreen(80, 24)

    # a) init.
    assert hasattr(screen, "dirty")
    assert isinstance(screen.dirty, set)
    assert screen.dirty == set(range(screen.lines))

    # b) reset().
    screen.dirty.clear()
    screen.reset()
    assert screen.dirty == set(range(screen.lines))

    # c) resize().
    screen.dirty.clear()
    screen.resize(130, 24)
    assert screen.dirty == set(range(screen.lines))

    # d) alignment_display().
    screen.dirty.clear()
    screen.alignment_display()
    assert screen.dirty == set(range(screen.lines))


def test_mark_single_line():
    screen = pyte.DiffScreen(80, 24)

    # a) draw().
    screen.dirty.clear()
    screen.draw("f")
    assert len(screen.dirty) == 1
    assert screen.cursor.y in screen.dirty

    # b) rest ...
    for method in ["insert_characters", "delete_characters",
                   "erase_characters", "erase_in_line"]:
        screen.dirty.clear()
        getattr(screen, method)()
        assert len(screen.dirty) == 1
        assert screen.cursor.y in screen.dirty


def test_modes():
    # Making sure `DECSCNM` triggers a screen to be fully re-drawn.
    screen = pyte.DiffScreen(80, 24)

    screen.dirty.clear()
    screen.set_mode(mo.DECSCNM >> 5, private=True)
    assert screen.dirty == set(range(screen.lines))

    screen.dirty.clear()
    screen.reset_mode(mo.DECSCNM >> 5, private=True)
    assert screen.dirty == set(range(screen.lines))


def test_index():
    screen = pyte.DiffScreen(80, 24)
    screen.dirty.clear()

    # a) not at the bottom margin -- nothing is marked dirty.
    screen.index()
    assert not screen.dirty

    # b) whole screen is dirty.
    screen.cursor_to_line(24)
    screen.index()
    assert screen.dirty == set(range(screen.lines))


def test_reverse_index():
    screen = pyte.DiffScreen(80, 24)
    screen.dirty.clear()

    # a) not at the top margin -- whole screen is dirty.
    screen.reverse_index()
    assert screen.dirty == set(range(screen.lines))

    # b) nothing is marked dirty.
    screen.dirty.clear()
    screen.cursor_to_line(screen.lines // 2)
    screen.reverse_index()
    assert not screen.dirty


def test_insert_delete_lines():
    screen = pyte.DiffScreen(80, 24)
    screen.cursor_to_line(screen.lines // 2)

    for method in ["insert_lines", "delete_lines"]:
        screen.dirty.clear()
        getattr(screen, method)()
        assert screen.dirty == set(range(screen.cursor.y, screen.lines))


def test_erase_in_display():
    screen = pyte.DiffScreen(80, 24)
    screen.cursor_to_line(screen.lines // 2)

    # a) from cursor to the end of the screen.
    screen.dirty.clear()
    screen.erase_in_display()
    assert screen.dirty == set(range(screen.cursor.y, screen.lines))

    # b) from the beginning of the screen to cursor.
    screen.dirty.clear()
    screen.erase_in_display(1)
    assert screen.dirty == set(range(0, screen.cursor.y + 1))

    # c) whole screen.
    screen.dirty.clear()
    screen.erase_in_display(2)
    assert screen.dirty == set(range(0, screen.lines))

    screen.dirty.clear()
    screen.erase_in_display(3)
    assert screen.dirty == set(range(0, screen.lines))


def test_draw_wrap():
    screen = pyte.DiffScreen(80, 24)
    screen.set_mode(mo.DECAWM)

    # fill every character cell on the first row
    for _ in range(80):
        screen.draw("g")
    assert screen.cursor.y == 0
    screen.dirty.clear()

    # now write one more character which should cause wrapping
    screen.draw("h")
    assert screen.cursor.y == 1
    # regression test issue #36 where the wrong line was marked as
    # dirty
    assert screen.dirty == {0, 1}


def test_draw_multiple_chars_wrap():
    screen = pyte.Screen(5, 2)
    screen.dirty.clear()
    screen.draw("1234567890")
    assert screen.cursor.y == 1
    assert screen.dirty == {0, 1}
