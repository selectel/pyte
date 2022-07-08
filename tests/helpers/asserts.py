from wcwidth import wcwidth
def consistency_asserts(screen):
    # Ensure that all the cells in the buffer, if they have
    # a data of 2 or more code points, they all sum up 0 width
    # In other words, the width of the cell is determinated by the
    # width of the first code point.
    for y in range(screen.lines):
        for x in range(screen.columns):
            data = screen.buffer[y][x].data
            assert sum(map(wcwidth, data[1:])) == 0


    # Ensure consistency between the real width (computed here
    # with wcwidth(...)) and the char.width attribute
    for y in range(screen.lines):
        for x in range(screen.columns):
            char = screen.buffer[y][x]
            if char.data:
                assert wcwidth(char.data[0]) == char.width
            else:
                assert char.data == ""
                assert char.width == 0

    # we check that no char is outside of the buffer
    # we need to check the internal _buffer for this and do an educated
    # check
    non_empty_y = list(screen._buffer.keys())
    min_y = min(non_empty_y) if non_empty_y else 0
    max_y = max(non_empty_y) if non_empty_y else screen.lines - 1

    assert 0 <= min_y <= max_y < screen.lines

    for line in screen._buffer.values():
        non_empty_x = list(line.keys())
        min_x = min(non_empty_x) if non_empty_x else 0
        max_x = max(non_empty_x) if non_empty_x else screen.columns - 1

        assert 0 <= min_x <= max_x < screen.columns
