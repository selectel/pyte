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
