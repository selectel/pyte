# -*- coding: utf-8 -*-
"""
    inception
    ~~~~~~~~~

    A terminal emulator within a terminal emulator within a terminal
    emulator -- tiny example to show how pagination works.

    :copyright: (c) 2011-2013 by Selectel, see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import print_function, unicode_literals

import os
import random
import string
import sys
sys.path.append("..")

if sys.version_info[0] == 2:
    input = raw_input

import pyte
from pyte import modes as mo


def print_screen(screen, text):
    print(pyte.ctrl.ESC + pyte.esc.RIS)

    for idx, line in enumerate(screen.display, 1):
        print("{0:2d} {1} ¶".format(idx, line))

    input(os.linesep + os.linesep + text)


def random_string(n, alphabet=string.ascii_letters + " "):
    return "".join(random.choice(alphabet) for _ in range(n))


if __name__ == "__main__":
    stream = pyte.Stream()  #             v -- means scroll whole page.
    screen = pyte.HistoryScreen(80, 12, ratio=1)
    screen.set_mode(mo.LNM)
    stream.attach(screen)

    pages = 3
    stream.feed(os.linesep.join(random_string(screen.columns)
                                for _ in range(screen.lines * pages)))
    screen.prev_page()

    print_screen(screen, "Hit ENTER to move up!")
    screen.prev_page()
    print_screen(screen, "Hit ENTER to move back down!")
    screen.next_page()
    print_screen(screen, "OK?")
