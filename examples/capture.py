# -*- coding: utf-8 -*-
"""
    capture
    ~~~~~~~

    An example showing how to feed :class:`~pyte.streams.Stream` from
    a running terminal app.

    :copyright: (c) 2015 by pyte authors and contributors,
                see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import print_function, unicode_literals

import codecs
import os
import pty
import select
import subprocess
import sys

import pyte


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        sys.exit("usage: %prog% command [args]")

    stream = pyte.Stream()
    screen = pyte.Screen(80, 24)
    stream.attach(screen)

    decoder = codecs.getincrementaldecoder(sys.getdefaultencoding())("replace")
    master, slave = pty.openpty()
    p = subprocess.Popen(sys.argv[1:], stdout=slave, stderr=slave)
    while True:
        try:
            [fd], _wlist, _xlist = select.select([master], [], [], 1)
        except (KeyboardInterrupt,  # Stop right now!
                ValueError):        # Nothing to read.
            p.kill()
            break
        else:
            stream.feed(decoder.decode(os.read(fd, 1024)))

    print(*screen.display, sep="\n")
