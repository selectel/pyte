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
    stream = pyte.Stream(screen)

    pid, master_fd = pty.fork()
    if pid == 0:  # Child.
        os.execvpe(sys.argv[1], sys.argv[1:],
                   env=dict(COLUMNS="80", LINES="24"))

    while True:
        try:
            [fd], _wlist, _xlist = select.select([master_fd], [], [], 1)
        except (KeyboardInterrupt,  # Stop right now!
                ValueError):        # Nothing to read.
            os.kill(pid, signal.SIGTERM)
            break
        else:
            stream.feed(os.read(fd, 1024))

    print(*screen.display, sep="\n")
