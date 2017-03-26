# -*- coding: utf-8 -*-
"""
    capture
    ~~~~~~~

    An example showing how to capure output from a running terminal app.

    :copyright: (c) 2015 by pyte authors and contributors,
                see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import print_function, unicode_literals

import os
import pty
import signal
import select
import sys

import pyte


if __name__ == "__main__":
    try:
        output_path, *argv = sys.argv[1:]
    except ValueError:
        sys.exit("usage: %prog% output command [args]")

    stream = pyte.Stream(pyte.Screen(80, 24))

    p_pid, master_fd = pty.fork()
    if p_pid == 0:  # Child.
        os.execvpe(argv[0], argv,
                   env=dict(TERM="linux", COLUMNS="80", LINES="24"))

    with open(output_path, "wb") as handle:
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

                handle.write(data)

        os.kill(p_pid, signal.SIGTERM)
