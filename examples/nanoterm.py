# -*- coding: utf-8 -*-
"""
    nanoterm
    ~~~~~~~~

    An example showing how to feed :class:`~pyte.streams.Stream` from
    a running terminal app.

    :copyright: (c) 2015 by pyte authors and contributors,
                see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import print_function, unicode_literals

import os
import pty
import select
import signal
import sys

import pyte


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        sys.exit("usage: %prog% command [args]")

    screen = pyte.Screen(80, 24)
    stream = pyte.ByteStream(screen)

    p_pid, master_fd = pty.fork()
    if p_pid == 0:  # Child.
        os.execvpe(sys.argv[1], sys.argv[1:],
                   env=dict(TERM="linux", COLUMNS="80", LINES="24"))

    while True:
        try:
            [_master_fd], _wlist, _xlist = select.select(
                [master_fd], [], [], 1)
        except (KeyboardInterrupt,  # Stop right now!
                ValueError):        # Nothing to read.
            break
        else:
            data = os.read(master_fd, 1024)
            if not data:
                break

            stream.feed(data)

    os.kill(p_pid, signal.SIGTERM)
    print(*screen.display, sep="\n")
